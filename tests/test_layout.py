from bloom import hid_usages, layout


def test_ansi_tenkeyless_has_87_keys_and_only_fn_without_a_key_name():
    assert len(layout.KEYS) == 87
    assert [k.legend for k in layout.KEYS if k.name is None] == ["Fn"]


def test_every_key_name_is_known_and_used_once():
    names = [k.name for k in layout.KEYS if k.name is not None]
    assert all(hid_usages.normalise(n) == n for n in names)
    assert len(names) == len(set(names))


def test_keys_do_not_overlap():
    for i, a in enumerate(layout.KEYS):
        for b in layout.KEYS[i + 1 :]:
            if a.y == b.y:
                assert a.x + a.width <= b.x or b.x + b.width <= a.x, (a.legend, b.legend)


def test_key_titles_spell_out_the_side_and_the_short_legends():
    assert layout.BY_NAME["left_option"].title == "Left Alt"
    assert layout.BY_NAME["caps_lock"].title == "Caps Lock"
    assert layout.BY_NAME["a"].title == "A"
