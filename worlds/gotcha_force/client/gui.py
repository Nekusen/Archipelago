# I disable these cause PyRight complains about them and I don't think there's anything I can about it
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Final

from CommonClient import logger

from . import tracker
from .tracker import (
    GO_MODE_GREEN,
    GO_MODE_RED,
    LINE_HAVE,
    LINE_INFO,
    LINE_MISSING,
    ROW_IN_LOGIC,
    ROW_OUT_OF_LOGIC,
    ROW_UNAVAILABLE,
    InventoryGroup,
    MissionRow,
    TrackerSection,
)

if TYPE_CHECKING:
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.layout import Layout
    from kivy.uix.togglebutton import ToggleButton
    from kivy.uix.treeview import TreeView, TreeViewNode
    from kivymd.uix.scrollview import MDScrollView
    from kvui import GameManager

    from . import GotchaForceContext

GO_MODE_TEXT: Final = {True: f"Go Mode: [color={GO_MODE_GREEN}]Yes[/color]",
                       False: f"Go Mode: [color={GO_MODE_RED}]No[/color]"}

ROW_MARKS: Final = {ROW_IN_LOGIC: "",
                    ROW_OUT_OF_LOGIC: "  [out of logic]",
                    ROW_UNAVAILABLE: "  [unavailable]"}
ROW_CHAPTER_COLORS: Final = {ROW_IN_LOGIC: (1, 1, 1, 1),
                             ROW_OUT_OF_LOGIC: (1, 1, 1, 0.45),
                             ROW_UNAVAILABLE: (1, 0.75, 0.75, 0.35)}
ROW_CHECK_COLORS: Final = {ROW_IN_LOGIC: (0.8, 0.95, 1, 1),
                           ROW_OUT_OF_LOGIC: (1, 1, 1, 0.4),
                           ROW_UNAVAILABLE: (1, 0.85, 0.85, 0.3)}
ZONE_TITLE_COLOR: Final = (1, 0.85, 0.3, 1)
INVENTORY_TITLE_COLOR: Final = (0.55, 0.9, 0.75, 1)
LINE_COLORS: Final = {LINE_HAVE: (1, 1, 1, 1),
                      LINE_MISSING: (1, 1, 1, 0.45),
                      LINE_INFO: (0.8, 0.95, 1, 1)}
WAITING_TEXT: Final = {True: "Waiting for the game...",
                       False: "Waiting for the server and the game..."}
INVENTORY_WAITING_TEXT: Final = "Waiting for the server..."
NO_CHECKS_TEXT: Final = "No checks left to show."
NOTE_COLOR: Final = (1, 1, 1, 0.7)

TOGGLES: Final = (("Show out of logic", True), ("Show unavailable", False), ("Show gacha spoilers", False))

TOGGLE_WIDTH: Final = 150
TOGGLE_HEIGHT: Final = 28
BAR_HEIGHT: Final = 32
BAR_SPACING: Final = 6
BAR_PADDING_X: Final = 4
BAR_PADDING_Y: Final = 2
LABEL_MARGIN: Final = 12
TREE_INDENT: Final = 18
TOGGLE_ON: Final = "down"
TOGGLE_OFF: Final = "normal"
REFRESH_SECONDS: Final = 1.0


def build_manager(ctx: GotchaForceContext, ui: type[GameManager]) -> type[GameManager]:
    class GotchaForceManager(ui):
        tracker_tree: TreeView
        inventory_tree: TreeView
        show_out_of_logic_toggle: ToggleButton
        show_unavailable_toggle: ToggleButton
        show_spoilers_toggle: ToggleButton
        tracker_go_mode: Label
        _tracker_signature: str | None
        _inventory_signature: str | None
        _tracker_folds: dict[str, bool]

        def build(self) -> Layout:
            container = super().build()
            from kivy.clock import Clock
            from kivy.uix.boxlayout import BoxLayout

            self.tracker_tree, tracker_view = self._scrolled_tree()
            self.inventory_tree, inventory_view = self._scrolled_tree()
            self.show_out_of_logic_toggle, self.show_unavailable_toggle, self.show_spoilers_toggle = (
                self._toggle_button(text, on) for text, on in TOGGLES
            )
            self.tracker_go_mode = self._go_mode_label()
            root = BoxLayout(orientation="vertical")
            root.add_widget(self._toggle_bar())
            root.add_widget(tracker_view)
            self.add_client_tab("Tracker", root)
            self.add_client_tab("Inventory", inventory_view)
            self._tracker_signature = None
            self._inventory_signature = None
            self._tracker_folds: dict[str, bool] = {}
            Clock.schedule_interval(self.update_tracker, REFRESH_SECONDS)
            return container

        @staticmethod
        def _scrolled_tree() -> tuple[TreeView, MDScrollView]:
            from kivy.metrics import dp
            from kivy.uix.treeview import TreeView
            from kivymd.uix.scrollview import MDScrollView
            tree = TreeView(hide_root=True, size_hint_y=None,
                            indent_level=dp(TREE_INDENT))
            tree.bind(minimum_height=tree.setter("height"))
            view = MDScrollView(do_scroll_x=False)
            view.add_widget(tree)
            return tree, view

        def _toggle_button(self, text: str, starts_on: bool) -> ToggleButton:
            from kivy.metrics import dp
            from kivy.uix.togglebutton import ToggleButton
            button = ToggleButton(
                text=text, state=TOGGLE_ON if starts_on else TOGGLE_OFF,
                size_hint=(None, None), width=dp(TOGGLE_WIDTH), height=dp(TOGGLE_HEIGHT)
            )
            button.bind(state=self._tracker_toggle)
            return button

        def _go_mode_label(self) -> Label:
            from kivy.metrics import dp
            from kivy.uix.label import Label
            label = Label(text=GO_MODE_TEXT[False], markup=True,
                          size_hint=(None, None), height=dp(TOGGLE_HEIGHT))
            label.bind(texture_size=self._fit_width_to_text)
            return label

        @staticmethod
        def _fit_width_to_text(label: Label, texture_size: Sequence[float]) -> None:
            from kivy.metrics import dp
            label.width = texture_size[0] + dp(LABEL_MARGIN)

        def _toggle_bar(self) -> BoxLayout:
            from kivy.metrics import dp
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.widget import Widget
            bar = BoxLayout(size_hint_y=None, height=dp(BAR_HEIGHT),
                            spacing=dp(BAR_SPACING), padding=(dp(BAR_PADDING_X), dp(BAR_PADDING_Y)))
            for button in (self.show_out_of_logic_toggle, self.show_unavailable_toggle,
                           self.show_spoilers_toggle):
                bar.add_widget(button)
            bar.add_widget(self.tracker_go_mode)
            bar.add_widget(Widget())
            return bar

        def _tracker_toggle(self, *_args: object) -> None:
            self._refresh_now()

        def _refresh_now(self) -> None:
            self._tracker_signature = None
            self.update_tracker(0)

        def _remember_fold(self, key: str, is_open: bool) -> None:
            self._tracker_folds[key] = is_open

        def _fold_node(self, tree: TreeView, key: str, text: str, color: tuple[float, ...],
                       default_open: bool, parent: TreeViewNode | None = None,
                       markup: bool = False) -> TreeViewNode:
            from kivy.uix.treeview import TreeViewLabel
            node = TreeViewLabel(
                text=text, bold=True, markup=markup, color=color,
                is_open=self._tracker_folds.get(key, default_open)
            )
            node.bind(is_open=lambda _node, value: self._remember_fold(key, value))
            return tree.add_node(node, parent)

        @staticmethod
        def _clear(tree: TreeView) -> None:
            for node in list(tree.iterate_all_nodes()):
                tree.remove_node(node)

        def _read_context(self) -> tuple | None:
            try:
                return (ctx.go_mode(), ctx.inventory_groups(),
                        ctx.tracker_rows(self.show_out_of_logic_toggle.state == TOGGLE_ON,
                                         self.show_unavailable_toggle.state == TOGGLE_ON))
            except Exception:
                logger.debug("tracker refresh failed", exc_info=True)
                return None

        def update_tracker(self, _dt: float) -> None:
            snapshot = self._read_context()
            if snapshot is None:
                return
            go_mode, groups, sections = snapshot
            self.tracker_go_mode.text = GO_MODE_TEXT[bool(go_mode)]
            self._update_inventory(groups)
            self._update_rows(sections, groups is not None,
                              self.show_spoilers_toggle.state == TOGGLE_ON)

        def _update_inventory(self, groups: list[InventoryGroup] | None) -> None:
            from kivy.uix.treeview import TreeViewLabel
            signature = repr(groups)
            if signature == self._inventory_signature:
                return
            self._inventory_signature = signature
            tree = self.inventory_tree
            self._clear(tree)
            if groups is None:
                tree.add_node(TreeViewLabel(text=INVENTORY_WAITING_TEXT, color=NOTE_COLOR))
                return
            for group in groups:
                node = self._fold_node(
                    tree, f"inventory:{group.key}", group.title,
                    INVENTORY_TITLE_COLOR, group.open, markup=True
                )
                for state, text in group.lines:
                    tree.add_node(TreeViewLabel(text=text, markup=True, color=LINE_COLORS[state]), node)

        def _update_rows(self, sections: list[TrackerSection] | None, connected: bool,
                         spoilers: bool) -> None:
            from kivy.uix.treeview import TreeViewLabel
            signature = repr(sections)
            if signature == self._tracker_signature:
                return
            self._tracker_signature = signature
            tree = self.tracker_tree
            self._clear(tree)
            if sections is None:
                tree.add_node(TreeViewLabel(text=WAITING_TEXT[connected], color=NOTE_COLOR))
                return
            if not sections:
                tree.add_node(TreeViewLabel(text=NO_CHECKS_TEXT, color=NOTE_COLOR))
                return
            recruited = ctx.unlocked_partners()
            for tile, zone, rows in sections:
                zone_node = self._fold_node(tree, f"zone:{tile}", f"{zone} ({_zone_total(rows)})",
                                            ZONE_TITLE_COLOR, True)
                for row in rows:
                    self._add_mission_row(tree, zone_node, row, recruited, spoilers)

        @staticmethod
        def _add_mission_row(tree: TreeView, zone_node: TreeViewNode, row: MissionRow,
                             recruited: set[int] | None, spoilers: bool) -> None:
            from kivy.uix.treeview import TreeViewLabel
            chapter_node = tree.add_node(TreeViewLabel(
                text=_row_text(row, recruited), color=ROW_CHAPTER_COLORS[row.state]
            ), zone_node)
            names = row.names if spoilers else tracker.hide_gacha_spoilers(row.names)
            for name in names:
                tree.add_node(TreeViewLabel(text=name, color=ROW_CHECK_COLORS[row.state]), chapter_node)

    return GotchaForceManager


def _zone_total(rows: Iterable[MissionRow]) -> int:
    return sum(tracker.row_count(row.names) for row in rows if row.state == ROW_IN_LOGIC)


def _row_text(row: MissionRow, recruited: set[int] | None) -> str:
    return f"{tracker.chapter_label(row.chapter)} ({tracker.row_count(row.names)}){_unavailable_mark(row, recruited)}"


def _unavailable_mark(row: MissionRow, recruited: set[int] | None) -> str:
    mark = ROW_MARKS[row.state]
    if row.state == ROW_UNAVAILABLE and recruited is not None and isinstance(row.chapter, int):
        hint = tracker.partner_hint(row.chapter, recruited)
        if hint:
            mark = f"  [unavailable: {hint}]"
    return mark
