# Themes

A theme changes how the site looks, not what it says. The engine renders the
same semantic HTML for every theme; a theme overrides it at three levels.

| Level | File | Changes |
|---|---|---|
| 1. Tokens | `tokens.css` (required) | colours, fonts, type scale, spacing |
| 2. Components | `theme.css` | the look of a component, through its stable class |
| 3. Templates | `templates/` | the markup of a component, one file at a time |

## Choosing a theme

Set `SITE_THEME` to the theme's directory name. The engine ships one theme,
`base`: black, white and greys on system fonts. An instance keeps its own themes in directories listed in `SITE_THEME_DIRS`
(comma-separated); those are searched before the engine's. An instance theme
named `base` replaces the engine's, so it must set every required token.

```text
themes/<name>/
  theme.toml      name, version, engine version, font stylesheets
  tokens.css      level 1
  theme.css       level 2, optional
  templates/      level 3, optional; same paths as the engine's templates
  static/         fonts, textures, icons; reach them from theme.css by relative URL
```

`theme.toml`:

```toml
name = "Dusk"
version = "1.0.0"
engine = "0.1"        # the engine release the theme is built for
fonts = ["https://fonts.googleapis.com/css2?family=Gabarito&display=swap"]
```

Every page loads, in order: the font stylesheets, `base/tokens.css`, the
theme's `tokens.css`, the engine's `base.css`, the theme's `theme.css`, then
the content type colours from the admin. A theme's `tokens.css` therefore sets
only the tokens it changes.

## Tokens

The token list is the engine's public API. Renaming or removing a token is a
breaking change.

| Group | Tokens |
|---|---|
| Surfaces | `--color-bg`, `--color-surface`, `--color-surface-2`, `--color-surface-band` |
| Text | `--color-text`, `--color-text-strong`, `--color-text-muted` |
| Lines | `--color-border`, `--color-border-soft` |
| Links | `--color-link`, `--color-link-hover` |
| Brand | `--color-brand`, `--color-brand-contrast` (text on the brand colour) |
| Type fallback | `--color-type-default`, `--color-type-default-tint` |
| Fonts | `--font-body`, `--font-display`, `--font-label` |
| Type scale | `--text-base`, `--text-label`, `--text-h1`, `--text-h1-detail`, `--text-h2` |
| Spacing | `--space-1` … `--space-9`, `--max-width`, `--gutter` |

The engine reads tokens only from top-level `:root` rules. A dark scheme sets
tokens again inside `@media (prefers-color-scheme: dark) { :root { … } }`.

`--color-bg`, `--color-text`, `--color-brand`, `--color-brand-contrast`,
`--color-type-default` and `--color-type-default-tint` must be `#rrggbb`, so
that their contrast can be checked. A `tokens.css` that does not parse, or sets
one of these to anything else, stops the start.

### Content type colours

Content type colours are not tokens: each type's colour and tint are set in the
admin and emitted as `[data-type="<key>"] { --type-color; --type-tint }`.
The tint mixes 12% of the colour into `--color-bg`, so it follows the dark
scheme; a tint set in the admin replaces it in the light scheme only.
Components read only `--type-color` and `--type-tint`, so a door, a card, a
menu marker and a what's-new line all take the colour of their type.

## Component classes

Stable, BEM-style. Target these from `theme.css`.

| Component | Classes |
|---|---|
| Page frame | `.site-header`, `.site-logo`, `.site-logo__mark`, `.site-logo__name`, `.site-logo__handle`, `.site-nav`, `.site-footer`, `.site-footer__inner`, `.footer-links` |
| Layout | `.container`, `.page`, `.page__title`, `.page__lead`, `.section-title`, `.label`, `.empty`, `.notice` |
| Buttons and forms | `.btn`, `.btn--primary`, `.btn--type`, `.input`, `.form`, `.form__field`, `.form__errors`, `.newsletter`, `.newsletter__title`, `.newsletter__row` |
| Home | `.hero`, `.hero__name`, `.hero__name--quiet`, `.hero__stats`, `.hero__lead`, `.hero__portrait`, `.hero__aside`, `.hero__actions`, `.home-doors`, `.doors`, `.door`, `.door__label`, `.door__title`, `.door__meta`, `.door__image`, `.door__more`, `.home-bottom`, `.home-bottom__aside`, `.next-up__label`, `.next-up__title`, `.follow`, `.follow__title` |
| Lists | `.cards`, `.card`, `.card__image`, `.card__title`, `.card__summary`, `.card__meta`, `.type-label`, `.stats`, `.filters`, `.pagination`, `.gallery`, `.gallery__item`, `.feed`, `.feed__item`, `.feed__type`, `.feed__title`, `.feed__meta`, `.feed__change`, `.chip`, `.timeline` |
| Detail pages | `.breadcrumb`, `.detail-hero`, `.detail-hero__title`, `.detail-hero__summary`, `.detail-hero__cover`, `.detail-layout`, `.detail-layout__main`, `.detail-layout__aside`, `.panel`, `.panel--typed`, `.panel__title`, `.panel__label`, `.related-item`, `.author-box` |
| Parts | `.part-text`, `.part-figure`, `.part-audio`, `.video-facade`, `.video-facade__play`, `.link-card`, `.link-card__icon` |
| Frames | `.framed`, `.framed__inner`; set `--frame-color` and `--frame-tint` to recolour |

## Overriding a template

Copy the engine's template to the same path under the theme's `templates/`,
for example `templates/lapidarium/components/door.html`. Components are small
files so that an override replaces one piece, not a page.

## Checks

`manage.py check` (and every start) checks the active theme:

| Id | Level | When |
|---|---|---|
| `lapidarium.E001` | error | a required token is defined by neither the base nor the theme |
| `lapidarium.E002` | error | text, brand or type fallback colour has contrast below 4.5:1 against its background, in either scheme |
| `lapidarium.W001` | warning | `theme.toml` declares no engine version |
| `lapidarium.W002` | warning | the theme is built for another engine release |
| `lapidarium.W003` | warning | the theme overrides a template the engine no longer has |

Content type colours are checked when a type is saved in the admin, against the
active theme's `--color-bg`.

## Preview

Staff see every component on the site's own content at
`<ADMIN_URL>theme-preview/`, linked from the admin sidebar, together with the
check results.
