# Pin Portal games

Games shared for the Pin Portal game library (Game library tab, System group). The portal lists them from index.json and installs them with its own safety check.

Layout

  games/<id>/<id>.zip        the game, without music, in the portal's export layout
  games/<id>/info.json       name, author, about, hardware (p2kd, mpf or virtual), licence, version
  games/<id>/screenshot.png  optional
  index.json                 built by the Action from the above, never edited by hand
  reviewed.json              {id: sha256 of the zip a maintainer has read}, edited only by the maintainer
  tools/                     the check (library_check.py, the same file the portal uses) and the index builder

To share a game, use Check it and Send to the library in the portal. It opens a pull request here. The Action checks the game and, after a merge, rebuilds index.json.

A game marked reviewed has had its code read by the maintainer, and the mark only holds for that exact zip. Install only games you trust. Games must not contain Williams sounds, pictures or ROMs, or music the sender does not own.

To test the builder by hand: python3 tools/build_index.py --check
