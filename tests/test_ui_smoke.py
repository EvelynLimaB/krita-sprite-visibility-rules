import os
import sys
import types
import unittest


@unittest.skipUnless(os.environ.get("RUN_QT_SMOKE") == "1", "Qt smoke test is opt-in")
class UiSmokeTests(unittest.TestCase):
    def test_plugin_registers_and_docker_constructs_with_public_surface(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication, QDockWidget

        app_qt = QApplication.instance() or QApplication([])

        class FakeApplication:
            def __init__(self):
                self.factories = []
                self.settings = {}

            def addDockWidgetFactory(self, factory):
                self.factories.append(factory)

            def activeDocument(self):
                return None

            def activeWindow(self):
                return None

            def readSetting(self, group, name, default):
                return self.settings.get((group, name), default)

            def writeSetting(self, group, name, value):
                self.settings[(group, name)] = value

        fake_app = FakeApplication()

        class FakeKrita:
            @staticmethod
            def instance():
                return fake_app

        class FakeDockWidgetFactoryBase:
            DockRight = 1

        class FakeDockWidgetFactory:
            def __init__(self, factory_id, location, widget_class):
                self.factory_id = factory_id
                self.location = location
                self.widget_class = widget_class

        fake_krita = types.ModuleType("krita")
        fake_krita.Krita = FakeKrita
        fake_krita.DockWidget = QDockWidget
        fake_krita.DockWidgetFactory = FakeDockWidgetFactory
        fake_krita.DockWidgetFactoryBase = FakeDockWidgetFactoryBase
        sys.modules["krita"] = fake_krita

        for module_name in list(sys.modules):
            if module_name == "sprite_visibility_rules" or module_name.startswith(
                "sprite_visibility_rules."
            ):
                del sys.modules[module_name]

        import sprite_visibility_rules  # noqa: F401

        self.assertEqual(len(fake_app.factories), 1)
        factory = fake_app.factories[0]
        self.assertEqual(factory.factory_id, "sprite_visibility_rules_docker")

        docker = factory.widget_class()
        try:
            self.assertEqual(docker.windowTitle(), "Sprite Visibility Rules")
            self.assertTrue(docker.timer.isActive())
            self.assertEqual(docker.controller.rules, [])
            docker.pause_checkbox.setChecked(True)
            self.assertTrue(docker.controller.paused)
            docker.interval_spin.setValue(200)
            self.assertEqual(docker.timer.interval(), 200)

            class FakeRoot:
                def childNodes(self):
                    return []

            class FakeDocument:
                def annotationTypes(self):
                    return []

                def rootNode(self):
                    return FakeRoot()

                def activeNode(self):
                    return None

                def name(self):
                    return "Canvas document"

                def fileName(self):
                    return ""

            class FakeView:
                def __init__(self, document):
                    self._document = document

                def document(self):
                    return self._document

            class FakeCanvas:
                def __init__(self, document):
                    self._view = FakeView(document)

                def view(self):
                    return self._view

            canvas_document = FakeDocument()
            docker.canvasChanged(FakeCanvas(canvas_document))
            self.assertIs(docker.controller.document, canvas_document)

            from sprite_visibility_rules.models import NodeRef, RuleKind, VisibilityRule

            docker.controller.rules = [
                VisibilityRule("first", RuleKind.LINKED, [NodeRef("a", "A"), NodeRef("b", "B")]),
                VisibilityRule("second", RuleKind.LINKED, [NodeRef("c", "C"), NodeRef("d", "D")]),
            ]
            docker.refresh_tree()
            docker.rule_tree.setCurrentItem(docker.rule_tree.topLevelItem(0))
            original_order = [rule.name for rule in docker.controller.rules]
            original_save = docker._save_and_refresh
            docker._save_and_refresh = lambda *args, **kwargs: False
            try:
                docker.move_rule(1)
            finally:
                docker._save_and_refresh = original_save
            self.assertEqual([rule.name for rule in docker.controller.rules], original_order)
        finally:
            docker.timer.stop()
            docker.close()
            app_qt.processEvents()


if __name__ == "__main__":
    unittest.main()
