#!/usr/bin/env python3
"""
Magpie Resolution Scaler for Linux Mint
HiDPI / fractional display scaling via xrandr
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango
import subprocess
import re
import sys


# ─── xrandr helpers ──────────────────────────────────────────────────────────

def get_displays():
    """Parse connected displays + their native resolutions from xrandr."""
    try:
        result = subprocess.run(['xrandr', '--query'], capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        return []

    displays = []
    current = None

    for line in result.stdout.splitlines():
        m = re.match(r'^(\S+)\s+(connected|disconnected)\s+(?:primary\s+)?(\d+x\d+)?', line)
        if m:
            if m.group(2) == 'connected':
                current = {
                    'name': m.group(1),
                    'resolution': m.group(3) or '',
                    'modes': []
                }
                displays.append(current)
            else:
                current = None
        elif current:
            mm = re.match(r'^\s+(\d+x\d+)\s+', line)
            if mm:
                current['modes'].append(mm.group(1))

    return displays


def effective_resolution(native_res: str, scale: float) -> str:
    """Calculate logical resolution after scaling."""
    try:
        w, h = map(int, native_res.split('x'))
        return f"{int(w / scale)} × {int(h / scale)} logical"
    except Exception:
        return ""


def apply_scale(display_name: str, scale: float, filter_name: str):
    cmd = [
        'xrandr',
        '--output', display_name,
        '--scale', f'{scale}x{scale}',
        '--filter', filter_name
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr.strip()


def reset_scale(display_name: str):
    cmd = ['xrandr', '--output', display_name, '--scale', '1x1']
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr.strip()


# ─── GUI ─────────────────────────────────────────────────────────────────────

CSS = b"""
window {
    background-color: #2b2b2b;
}
.title-label {
    font-size: 18px;
    font-weight: bold;
    color: #e8e8e8;
}
.subtitle-label {
    font-size: 12px;
    color: #999999;
}
.section-label {
    font-size: 11px;
    font-weight: bold;
    color: #aaaaaa;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.field-label {
    font-size: 13px;
    color: #cccccc;
    min-width: 75px;
}
.status-ok {
    color: #6dcd6d;
    font-size: 12px;
}
.status-err {
    color: #f28b82;
    font-size: 12px;
}
.status-neutral {
    color: #aaaaaa;
    font-size: 12px;
}
.apply-btn {
    background: #4a90d9;
    color: white;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 18px;
    border: none;
}
.apply-btn:hover {
    background: #5ba3ec;
}
.reset-btn {
    background: #555555;
    color: #dddddd;
    border-radius: 6px;
    padding: 6px 14px;
    border: none;
}
.reset-btn:hover {
    background: #666666;
}
.preset-btn {
    background: #3a3a3a;
    color: #cccccc;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    border: 1px solid #555;
    min-width: 52px;
}
.preset-btn:hover {
    background: #4a4a4a;
    color: #ffffff;
}
.effective-label {
    font-size: 12px;
    color: #7ecbff;
    font-style: italic;
}
combobox, combo {
    background: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 4px;
}
scale trough {
    background: #3a3a3a;
    border-radius: 4px;
}
scale highlight {
    background: #4a90d9;
    border-radius: 4px;
}
"""


class MagpieScalerWindow(Gtk.Window):

    PRESETS = [
        ("75%",  0.75),
        ("90%",  0.90),
        ("100%", 1.00),
        ("125%", 1.25),
        ("150%", 1.50),
        ("175%", 1.75),
        ("200%", 2.00),
    ]

    FILTERS = [
        ("bilinear",   "Bilinear — smooth, good all-rounder"),
        ("nearest",    "Nearest Neighbor — crisp / pixel-perfect"),
        ("catmullrom", "Catmull-Rom — sharp with smooth curves"),
        ("mitchell",   "Mitchell — balanced sharpness"),
        ("lanczos",    "Lanczos — maximum sharpness (may not be available)"),
    ]

    def __init__(self):
        super().__init__(title="Magpie Resolution Scaler")
        self.set_default_size(500, 430)
        self.set_resizable(False)
        self.set_border_width(0)

        self.displays = get_displays()
        self._prev_scale = {}   # { display_name: (scale, filter) }
        self._cur_scale  = {}   # currently applied

        self._apply_css()
        self._build_ui()
        self._refresh_effective()

    # ── CSS ──────────────────────────────────────────────────────────────────

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        # ── Header bar ──
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header.set_margin_top(20)
        header.set_margin_start(24)
        header.set_margin_end(24)
        header.set_margin_bottom(14)

        title = Gtk.Label(label="🔍  Magpie Resolution Scaler")
        title.get_style_context().add_class('title-label')
        title.set_halign(Gtk.Align.START)

        subtitle = Gtk.Label(label="HiDPI fractional display scaling for Linux Mint")
        subtitle.get_style_context().add_class('subtitle-label')
        subtitle.set_halign(Gtk.Align.START)

        header.pack_start(title, False, False, 0)
        header.pack_start(subtitle, False, False, 0)
        root.pack_start(header, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(sep, False, False, 0)

        # ── Content ──
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_margin_top(18)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_bottom(16)
        root.pack_start(content, True, True, 0)

        # Display row
        content.pack_start(self._row("Display", self._make_display_combo()), False, False, 0)

        # Scale slider
        content.pack_start(self._row("Scale", self._make_scale_slider()), False, False, 0)

        # Presets row
        content.pack_start(self._row("Presets", self._make_presets()), False, False, 0)

        # Filter row
        content.pack_start(self._row("Filter", self._make_filter_combo()), False, False, 0)

        # Effective resolution hint
        self.effective_label = Gtk.Label()
        self.effective_label.get_style_context().add_class('effective-label')
        self.effective_label.set_halign(Gtk.Align.END)
        content.pack_start(self.effective_label, False, False, 0)

        # Status
        self.status_label = Gtk.Label(label="Select a display and scale factor, then click Apply.")
        self.status_label.get_style_context().add_class('status-neutral')
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_line_wrap(True)
        content.pack_start(self.status_label, False, False, 0)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        content.pack_start(sep2, False, False, 0)

        # Buttons
        content.pack_start(self._make_buttons(), False, False, 0)

        self.show_all()

        if not self.displays:
            self._set_status("⚠  No connected displays detected via xrandr.", 'err')

    def _row(self, label_text, widget):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label=label_text + ":")
        lbl.get_style_context().add_class('field-label')
        lbl.set_halign(Gtk.Align.END)
        lbl.set_valign(Gtk.Align.CENTER)
        lbl.set_size_request(75, -1)
        box.pack_start(lbl, False, False, 0)
        box.pack_start(widget, True, True, 0)
        return box

    def _make_display_combo(self):
        self.display_combo = Gtk.ComboBoxText()
        if self.displays:
            for d in self.displays:
                label = f"{d['name']}  ({d['resolution'] or '?'})"
                self.display_combo.append_text(label)
            self.display_combo.set_active(0)
        else:
            self.display_combo.append_text("No displays found")
            self.display_combo.set_active(0)
        self.display_combo.connect('changed', self._on_display_changed)
        return self.display_combo

    def _make_scale_slider(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.scale_adj = Gtk.Adjustment(value=1.0, lower=0.5, upper=2.5,
                                        step_increment=0.05, page_increment=0.25)
        self.scale_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                      adjustment=self.scale_adj)
        self.scale_slider.set_digits(2)
        self.scale_slider.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_slider.set_draw_value(True)
        for v in [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5]:
            self.scale_slider.add_mark(v, Gtk.PositionType.BOTTOM,
                                       str(v) if v in [0.5, 1.0, 1.5, 2.0, 2.5] else None)
        self.scale_adj.connect('value-changed', self._on_scale_changed)
        box.pack_start(self.scale_slider, True, True, 0)
        return box

    def _make_presets(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        for label, value in self.PRESETS:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class('preset-btn')
            btn.connect('clicked', lambda b, v=value: self.scale_adj.set_value(v))
            box.pack_start(btn, True, True, 0)
        return box

    def _make_filter_combo(self):
        self.filter_combo = Gtk.ComboBoxText()
        for fid, fname in self.FILTERS:
            self.filter_combo.append(fid, fname)
        self.filter_combo.set_active_id("bilinear")
        return self.filter_combo

    def _make_buttons(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.revert_btn = Gtk.Button(label="↩  Revert")
        self.revert_btn.get_style_context().add_class('reset-btn')
        self.revert_btn.connect('clicked', self._on_revert)
        self.revert_btn.set_sensitive(False)
        self.revert_btn.set_tooltip_text("Undo last apply")

        self.reset_btn = Gtk.Button(label="Reset 1:1")
        self.reset_btn.get_style_context().add_class('reset-btn')
        self.reset_btn.connect('clicked', self._on_reset)
        self.reset_btn.set_tooltip_text("Restore native resolution (no scaling)")

        self.apply_btn = Gtk.Button(label="Apply Scaling")
        self.apply_btn.get_style_context().add_class('apply-btn')
        self.apply_btn.connect('clicked', self._on_apply)

        box.pack_start(self.revert_btn, False, False, 0)
        box.pack_start(self.reset_btn, False, False, 0)
        box.pack_end(self.apply_btn, False, False, 0)
        return box

    # ── State helpers ────────────────────────────────────────────────────────

    def _get_display(self):
        idx = self.display_combo.get_active()
        if 0 <= idx < len(self.displays):
            return self.displays[idx]
        return None

    def _set_status(self, msg, kind='neutral'):
        classes = ['status-ok', 'status-err', 'status-neutral']
        ctx = self.status_label.get_style_context()
        for c in classes:
            ctx.remove_class(c)
        ctx.add_class(f'status-{kind}')
        self.status_label.set_text(msg)

    def _refresh_effective(self):
        d = self._get_display()
        scale = self.scale_adj.get_value()
        if d and d['resolution']:
            eff = effective_resolution(d['resolution'], scale)
            if scale == 1.0:
                self.effective_label.set_text(f"Native resolution  ({d['resolution']})")
            else:
                self.effective_label.set_text(
                    f"Effective: {eff}  (native {d['resolution']})"
                )
        else:
            self.effective_label.set_text("")

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_display_changed(self, combo):
        self._refresh_effective()

    def _on_scale_changed(self, adj):
        self._refresh_effective()

    def _on_apply(self, btn):
        d = self._get_display()
        if not d:
            return
        scale = self.scale_adj.get_value()
        filt  = self.filter_combo.get_active_id()

        # Save previous state for revert
        prev = self._cur_scale.get(d['name'])
        if prev:
            self._prev_scale[d['name']] = prev
        self._cur_scale[d['name']] = (scale, filt)

        self.apply_btn.set_sensitive(False)
        self._set_status(f"Applying {scale:.2f}× ({filt}) to {d['name']} …", 'neutral')

        GLib.timeout_add(60, self._do_apply, d['name'], scale, filt)

    def _do_apply(self, name, scale, filt):
        ok, err = apply_scale(name, scale, filt)
        if ok:
            self._set_status(f"✓  Applied {scale:.2f}× ({filt}) to {name}", 'ok')
            self.revert_btn.set_sensitive(name in self._prev_scale)
        else:
            self._set_status(f"✗  {err or 'xrandr returned an error.'}", 'err')
        self.apply_btn.set_sensitive(True)
        return False

    def _on_reset(self, btn):
        d = self._get_display()
        if not d:
            return
        ok, err = reset_scale(d['name'])
        if ok:
            self.scale_adj.set_value(1.0)
            self._cur_scale.pop(d['name'], None)
            self._set_status(f"✓  {d['name']} reset to native 1:1", 'ok')
            self.revert_btn.set_sensitive(False)
        else:
            self._set_status(f"✗  {err or 'xrandr returned an error.'}", 'err')

    def _on_revert(self, btn):
        d = self._get_display()
        if not d or d['name'] not in self._prev_scale:
            return
        scale, filt = self._prev_scale[d['name']]
        ok, err = apply_scale(d['name'], scale, filt)
        if ok:
            self.scale_adj.set_value(scale)
            self._set_status(f"↩  Reverted {d['name']} to {scale:.2f}× ({filt})", 'ok')
            self._cur_scale[d['name']] = (scale, filt)
            self._prev_scale.pop(d['name'], None)
            self.revert_btn.set_sensitive(False)
        else:
            self._set_status(f"✗  {err or 'Revert failed.'}", 'err')


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    # Verify xrandr is present
    if subprocess.run(['which', 'xrandr'], capture_output=True).returncode != 0:
        print("Error: xrandr not found.\nInstall with: sudo apt install x11-xserver-utils")
        sys.exit(1)

    win = MagpieScalerWindow()
    win.connect('destroy', Gtk.main_quit)
    Gtk.main()


if __name__ == '__main__':
    main()
