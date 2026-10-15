# Parts

An entry's body is an ordered list of parts. Kinds are code: each has a
template and a validator, registered in one place. Which kinds an entry may
and must have is set on its [content type](content-types.md).

| Kind | Needs | Renders as |
|---|---|---|
| `text` | Markdown | Sanitised HTML; the caption becomes a heading |
| `video` | URL | A link to the video that turns into the player on click (YouTube through youtube-nocookie, Vimeo, PeerTube); any other host is a link card |
| `audio` | Uploaded file or URL | An `<audio>` player for a file, a link card for a URL |
| `image` | Uploaded file with alt text | A `<figure>` with its caption |
| `file` | Uploaded file | A download card; `download_label` in its options names it |
| `link` | URL | A link card |

The media-first layout shows video, audio and image parts before the text; the
gallery layout puts the images in a grid. Nothing from a video host loads
until the reader presses play, and without JavaScript the facade is a plain
link to the video.
