"""Komponen tampilan kecil yang dipakai lintas halaman."""

import html

import streamlit as st


_ICON_PATHS = {
    "home": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-6v-7h-4v7H4a1 1 0 0 1-1-1z"/>',
    "lock": '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "key": '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9m-4 4 3 3m-6-1 3 3"/>',
    "chart": '<path d="M4 19V5m0 14h17M7 15l4-5 4 3 5-7"/>',
    "shield": '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 11v5m0-8h.01"/>',
}


def icon_svg(name: str, size: int = 18) -> str:
    path = _ICON_PATHS.get(name, _ICON_PATHS["info"])
    return (
        f'<svg aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round">{path}</svg>'
    )


def wordmark() -> None:
    st.markdown(
        f'<div class="wordmark">{icon_svg("shield", 22)}<span>Pixego</span></div>',
        unsafe_allow_html=True,
    )


def glass_card(content: str, icon: str | None = None, class_name: str = "") -> None:
    badge = f'<span class="feature-icon">{icon_svg(icon)}</span>' if icon else ""
    st.markdown(
        f'<section class="glass-card {html.escape(class_name)}">{badge}{content}</section>',
        unsafe_allow_html=True,
    )


def pill(text: str, icon: str | None = None, tone: str | None = None) -> None:
    prefix = icon_svg(icon, 14) if icon else ""
    tone_class = {"blue": "pill--blue", "violet": "pill--violet"}.get(tone, "")
    st.markdown(
        f'<span class="pill {tone_class}">{prefix}{html.escape(text)}</span>',
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        '<div class="stat-card">'
        f'<div class="stat-value">{html.escape(value)}</div>'
        f'<div class="stat-label">{html.escape(label)}</div>'
        f'{f"<div class=\"stat-note\">{html.escape(note)}</div>" if note else ""}'
        '</div>',
        unsafe_allow_html=True,
    )


def section_title(title: str, eyebrow: str | None = None) -> None:
    if eyebrow:
        st.markdown(f'<div class="page-kicker">{html.escape(eyebrow)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)


def footer() -> None:
    from app.config import FOOTER_TEXT
    from app.services import clear_session_data

    st.markdown(f'<div class="app-footer">{html.escape(FOOTER_TEXT)}</div>', unsafe_allow_html=True)
    st.button(
        "Hapus data sesi",
        key="pixego_clear_session_button",
        on_click=lambda: clear_session_data(st.session_state),
        help="Menghapus gambar dan nilai formulir dari sesi ini.",
    )


def render_navigation(nav_items: tuple[dict, ...], active_label: str) -> None:
    with st.container(key="pixego_nav"):
        columns = st.columns([1.15, 1, 1.25, .85, .9, .85], gap="small", vertical_alignment="center")
        with columns[0]:
            st.markdown(
                f'<div class="nav-brand">{icon_svg("shield", 20)}<span>Pixego</span></div>',
                unsafe_allow_html=True,
            )
        for column, item in zip(columns[1:], nav_items):
            with column:
                active = item["label"] == active_label
                with st.container(key="pixego_nav_active" if active else f"pixego_nav_{item['label'].lower()}"):
                    st.page_link(
                        item["file"],
                        label=item["label"],
                        icon=f':material/{item["icon"]}:',
                    )