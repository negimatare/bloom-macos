"""Keys tab: a table of 1:1 key mappings, plus press-a-key capture."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .. import hid_usages, mac_keycodes
from .controller import Controller


def _key_combo(selected: str | None = None) -> QComboBox:
    combo = QComboBox()
    for name in hid_usages.names():
        combo.addItem(hid_usages.label(name), name)
    if selected:
        combo.setCurrentIndex(combo.findData(selected))
    return combo


class CaptureDialog(QDialog):
    """Press the original key, then the key it should become."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Press keys")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.result_pair: tuple[str, str] | None = None
        self._src: str | None = None

        self.prompt = QLabel()
        self.prompt.setWordWrap(True)
        self.prompt.setAlignment(Qt.AlignCenter)
        font = self.prompt.font()
        font.setPointSize(font.pointSize() + 3)
        self.prompt.setFont(font)
        self.detail = QLabel()
        self.detail.setAlignment(Qt.AlignCenter)
        self.detail.setStyleSheet("color: gray;")

        cancel = QPushButton("Cancel")
        cancel.setFocusPolicy(Qt.NoFocus)
        cancel.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.prompt)
        layout.addWidget(self.detail)
        layout.addWidget(cancel, alignment=Qt.AlignCenter)
        self._show_step()

    def _show_step(self) -> None:
        if self._src is None:
            self.prompt.setText("Press the key you want to change")
            self.detail.setText("Your current mappings are paused while this window is open.")
        else:
            self.prompt.setText(
                f"<b>{hid_usages.label(self._src)}</b> should become…<br>press the new key"
            )
            self.detail.setText("")

    def event(self, event) -> bool:
        # Catch every key here, before Qt uses Tab/Escape/Return for itself.
        if event.type() == QEvent.ShortcutOverride:
            event.accept()
            return True
        if event.type() == QEvent.KeyPress and not event.isAutoRepeat():
            self._handle_key(event.nativeVirtualKey())
            return True
        return super().event(event)

    def _handle_key(self, virtual_key: int) -> None:
        name = mac_keycodes.name_for_virtual_key(virtual_key)
        if name is None:
            self.detail.setText("That key isn't supported. Pick it from the list instead.")
            return
        if self._src is None:
            self._src = name
            self._show_step()
        else:
            self.result_pair = (self._src, name)
            self.accept()


class KeysTab(QWidget):
    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.c = controller

        intro = QLabel(
            "Remap keys on the Razer only. Other keyboards, such as the MacBook's, "
            "are not affected."
        )
        intro.setWordWrap(True)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Becomes"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        capture = QPushButton("Press keys…")
        add = QPushButton("Add")
        remove = QPushButton("Remove")
        self.apply_button = QPushButton("Apply")
        self.apply_button.setDefault(True)
        self.revert_button = QPushButton("Revert")
        capture.clicked.connect(self._capture)
        add.clicked.connect(lambda: self._add_row("caps_lock", "escape"))
        remove.clicked.connect(self._remove_row)
        self.apply_button.clicked.connect(self._apply)
        self.revert_button.clicked.connect(self.refresh)

        buttons = QHBoxLayout()
        for b in (capture, add, remove):
            buttons.addWidget(b)
        buttons.addStretch(1)
        buttons.addWidget(self.revert_button)
        buttons.addWidget(self.apply_button)

        self.helper = QCheckBox("Keep mappings after reconnecting (background helper, starts at login)")
        self.helper.setChecked(self.c.helper_installed())
        self.helper.toggled.connect(self._on_helper)
        helper_note = QLabel(
            "macOS forgets key mappings when the keyboard is unplugged or the Mac restarts. "
            "The helper re-applies them automatically."
        )
        helper_note.setWordWrap(True)
        helper_note.setStyleSheet("color: gray;")

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        layout.addSpacing(8)
        layout.addWidget(self.helper)
        layout.addWidget(helper_note)

        self._profile_name = self.c.config.active_profile
        self.c.config_changed.connect(self._on_config_changed)
        self.refresh()

    def _on_helper(self, enabled: bool) -> None:
        self.c.set_helper(enabled)
        self.helper.blockSignals(True)
        self.helper.setChecked(self.c.helper_installed())
        self.helper.blockSignals(False)

    # ---- table ---------------------------------------------------------------

    def _rows(self) -> list[tuple[str, str]]:
        rows = []
        for r in range(self.table.rowCount()):
            src = self.table.cellWidget(r, 0).currentData()
            dst = self.table.cellWidget(r, 1).currentData()
            rows.append((src, dst))
        return rows

    def _add_row(self, src: str, dst: str, select: bool = True) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        for col, name in enumerate((src, dst)):
            combo = _key_combo(name)
            combo.currentIndexChanged.connect(self._update_dirty)
            self.table.setCellWidget(r, col, combo)
        if select:
            self.table.selectRow(r)
        self._update_dirty()

    def _remove_row(self) -> None:
        r = self.table.currentRow()
        if r < 0:
            r = self.table.rowCount() - 1
        if r >= 0:
            self.table.removeRow(r)
        self._update_dirty()

    def _capture(self) -> None:
        self.c.suspend_mappings()
        try:
            dialog = CaptureDialog(self)
            dialog.exec()
        finally:
            self.c.resume_mappings()
        if not dialog.result_pair:
            return
        src, dst = dialog.result_pair
        for r, (existing, _) in enumerate(self._rows()):
            if existing == src:  # update the existing row
                combo = self.table.cellWidget(r, 1)
                combo.setCurrentIndex(combo.findData(dst))
                self.table.selectRow(r)
                return
        self._add_row(src, dst)

    def _apply(self) -> None:
        if self.c.set_mappings(self._rows()):
            self.refresh()

    def _on_config_changed(self) -> None:
        # Keep unapplied edits, unless a different profile was selected.
        if self.c.config.active_profile != self._profile_name or not self._dirty():
            self.refresh()

    def refresh(self) -> None:
        self._profile_name = self.c.config.active_profile
        self.table.setRowCount(0)
        for src, dst in self.c.profile.mappings:
            self._add_row(src, dst, select=False)
        self._update_dirty()

    def _dirty(self) -> bool:
        return self._rows() != [tuple(m) for m in self.c.profile.mappings]

    def _update_dirty(self) -> None:
        dirty = self._dirty()
        self.apply_button.setEnabled(dirty)
        self.revert_button.setEnabled(dirty)
