# Interoperability with other Krita visibility plugins

Sprite Visibility Rules intentionally does **not** duplicate the manual commands provided by these plugins:

- `Pine885/krita-plugin-layer-visibility-switch`
- `LainFenrir/krita-sneaky-visibility`
- `chimera28/quicktogglehidden`

Its responsibility remains limited to persistent inverse, exclusive, and linked relationships between explicitly configured layers.

## Compatibility contract

Sprite Visibility Rules follows these rules when another plugin changes visibility:

1. It never consumes or blocks Qt mouse, shortcut, menu, or toolbar events. The shared application event broker always returns control to Krita.
2. It does not register action IDs for adjacent-layer navigation, selected-layer toggling, or label-color toggling.
3. It does not change layer color labels, blending modes, locks, selection, active-node position, or sibling order.
4. It observes only layers referenced by enabled rules. Visibility changes to unrelated layers are ignored.
5. If another plugin leaves a governed rule in a valid state, Sprite Visibility Rules performs no write and requests no projection refresh.
6. If another plugin leaves a governed rule in an invalid state, Sprite Visibility Rules applies only the minimum dependent corrections required by that rule.
7. A correction batch requests at most one `Document.refreshProjection()` regardless of the number of corrected layers.
8. The 32 ms settle countdown is armed only after the current Qt action returns, so synchronous actions from other plugins complete before enforcement can run.
9. Rapid events are coalesced into one pending rule scan.
10. The fallback polling timer remains available for changes made without input events, but stops when no enabled rule needs monitoring.
11. Rule creation and rebinding use the docker's own canvas selection, not another active Krita window.

## Plugin-specific behavior

### Layer Visibility Switch

This plugin hides the active sibling, selects an adjacent sibling, and shows it. When that transition already leaves an exclusive rule with one visible member, Sprite Visibility Rules accepts it without rewriting the result.

If the destination belongs to an inverse, linked, or exclusive rule and the final combination is invalid, only the dependent rule members are normalized. Sprite Visibility Rules does not alter the active layer selected by Layer Visibility Switch and does not reproduce its navigation commands.

### Sneaky Visibility

Sneaky Visibility toggles selected layers through its own action. Untracked selected layers remain entirely outside Sprite Visibility Rules.

When selected layers are members of a rule, the completed multi-layer result is evaluated as one observed state transition. A valid result is retained; an invalid result is normalized once after the action returns and the render-settle interval completes.

Sprite Visibility Rules does not attempt to reproduce Sneaky Visibility's undo behavior, shortcut, layer-menu item, toolbar action, or multi-selection toggle.

### QuickToggleHidden

QuickToggleHidden traverses label-colored layers and may update many nodes in one action. Sprite Visibility Rules first yields back to the event loop, then starts its settle timer, so it cannot run inside the label traversal or consume its shortcut event.

A complete color-label batch that already satisfies a linked or exclusive rule is accepted without another refresh. A partial or contradictory result is corrected once. Sprite Visibility Rules does not inspect or assign color labels and does not register label-color shortcut actions.

## Avoiding semantic conflicts

Compatibility does not mean that contradictory instructions can both remain visible. A configured rule is authoritative for its members.

For predictable files:

- Use Layer Visibility Switch for sibling navigation.
- Use Sneaky Visibility for temporary selected-layer operations.
- Use QuickToggleHidden for broad color-label categories.
- Use Sprite Visibility Rules only for layers that must maintain a persistent logical relationship.

A layer may be used by another plugin and by a Sprite Visibility Rule, but an external result that violates the configured rule will be normalized by design.

## Regression coverage

The test suite verifies:

- valid adjacent-sibling transitions are left untouched;
- unrelated selected-layer toggles are ignored;
- invalid multi-selection results are normalized once;
- valid label-color batches are left untouched;
- partial external batches receive only the minimum correction and one projection refresh;
- the settle timer starts only after the triggering action returns;
- inactive documents and rule sets do not keep the fallback timer running;
- all dockers share one application event broker;
- input from the plugin's own rule tree does not schedule a scan;
- canvas-local selection wins over another active window;
- rule compilation is invalidated by explicit revisions instead of per-scan signatures.
