import os
import sys
import types
import unittest
from unittest.mock import Mock


@unittest.skipUnless(os.environ.get("RUN_QT_SMOKE") == "1", "Qt smoke test is opt-in")
class UiSmokeTests(unittest.TestCase):
    def test_plugin_registers_and_docker_constructs_with_public_surface(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtCore import QEvent
        from PyQt5.QtTest import QTest
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
        second_docker = None
        try:
            self.assertEqual(docker.windowTitle(), "Sprite Visibility Rules")
            self.assertFalse(docker.timer.isActive())
            self.assertEqual(docker.controller.rules, [])
            self.assertEqual(docker.interval_spin.minimum(), 50)
            self.assertTrue(docker._input_settle_timer.isSingleShot())
            self.assertEqual(docker._input_settle_timer.interval(), 32)
            docker.interval_spin.setValue(200)
            self.assertEqual(docker.timer.interval(), 200)

            class FakeUuid:
                def __init__(self, value):
                    self.value = value

                def toString(self):
                    return self.value

            class FakeNode:
                def __init__(self, node_id, name):
                    self.node_id = node_id
                    self._name = name

                def uniqueId(self):
                    return FakeUuid(self.node_id)

                def name(self):
                    return self._name

                def childNodes(self):
                    return []

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

                def refreshProjection(self):
                    pass

            class FakeView:
                def __init__(self, document, selected=None):
                    self._document = document
                    self._selected = selected or []

                def document(self):
                    return self._document

                def selectedNodes(self):
                    return list(self._selected)

            class FakeCanvas:
                def __init__(self, document, selected=None):
                    self._view = FakeView(document, selected)

                def view(self):
                    return self._view

            canvas_document = FakeDocument()
            selected = [FakeNode("canvas-a", "Canvas A"), FakeNode("canvas-b", "Canvas B")]
            docker.canvasChanged(FakeCanvas(canvas_document, selected))
            self.assertIs(docker.controller.document, canvas_document)
            self.assertEqual(
                [ref.node_id for ref in docker._selected_refs()],
                ["canvas-a", "canvas-b"],
            )
            self.assertFalse(docker.timer.isActive())

            from sprite_visibility_rules.models import NodeRef, RuleKind, VisibilityRule
            from sprite_visibility_rules.qt_compat import MOUSE_BUTTON_RELEASE

            docker.controller.replace_rules(
                [
                    VisibilityRule(
                        "first",
                        RuleKind.LINKED,
                        [NodeRef("a", "A"), NodeRef("b", "B")],
                    ),
                    VisibilityRule(
                        "second",
                        RuleKind.LINKED,
                        [NodeRef("c", "C"), NodeRef("d", "D")],
                    ),
                ]
            )
            docker._update_monitoring_state(refresh_snapshot=True)
            self.assertTrue(docker.timer.isActive())

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

            own_event = QEvent(MOUSE_BUTTON_RELEASE)
            self.assertFalse(docker._input_should_wake(docker.rule_tree.viewport(), own_event))

            original_scan_once = docker._scan_once
            docker._scan_once = Mock()
            try:
                docker.request_scan()
                docker.request_scan()
                self.assertFalse(docker._input_settle_timer.isActive())
                app_qt.processEvents()
                self.assertTrue(docker._input_settle_timer.isActive())
                docker._scan_once.assert_not_called()
                QTest.qWait(45)
                app_qt.processEvents()
                docker._scan_once.assert_called_once_with(False)
            finally:
                docker._scan_once = original_scan_once

            docker.pause_checkbox.setChecked(True)
            self.assertTrue(docker.controller.paused)
            self.assertFalse(docker.timer.isActive())
            docker.pause_checkbox.setChecked(False)
            self.assertFalse(docker.controller.paused)
            self.assertTrue(docker.timer.isActive())

            docker.controller.set_rule_enabled(0, False)
            docker.controller.set_rule_enabled(1, False)
            docker._update_monitoring_state()
            self.assertFalse(docker.timer.isActive())

            second_docker = factory.widget_class()
            self.assertIs(second_docker._input_broker, docker._input_broker)
            self.assertGreaterEqual(docker._input_broker.registered_count, 2)
        finally:
            docker.scheduler.dispose()
            docker.close()
            if second_docker is not None:
                second_docker.scheduler.dispose()
                second_docker.close()
            app_qt.processEvents()


if __name__ == "__main__":
    unittest.main()
