# Pin Portal games

Games shared for the Pin Portal game library (Game library tab, System group). The portal lists them from index.json and installs them with its own safety check.

Layout

  games/<id>/<id>.zip        the game, without music, in the portal's export layout
  games/<id>/info.json       name, author, about, hardware (p2kd, mpf or virtual), licence, version, min_portal (oldest Pin Portal it works with)
  games/<id>/screenshot.png  optional
  index.json                 built by the Action from the above, never edited by hand
  reviewed.json              {id: sha256 of the zip a maintainer has read}, edited only by the maintainer
  issues.json                {id: GitHub issue number that holds the game comments}, kept by the Action
  tools/                     the check (library_check.py, the same file the portal uses) and the index builder

To share a game, use Check it and Send to the library in the portal. It opens a pull request here. The Action checks the game and, after a merge, rebuilds index.json.

A game marked reviewed has had its code read by the maintainer, and the mark only holds for that exact zip. Install only games you trust. Games must not contain Williams sounds, pictures or ROMs, or music the sender does not own.

To test the builder by hand: python3 tools/build_index.py --check

Versions

Every game has a version (1, 1.2, up to four numbers) and optionally min_portal, the oldest Pin Portal it works with. Both are in info.json and in the game.json inside the zip, and the Action refuses a game where they disagree. A game that is already listed can only be replaced by a higher version. The portal offers an update to anyone who has an older version installed, and refuses to install a game that needs a newer Pin Portal than the one running.

Comments

Each listed game gets one issue (made by the Action), and the Comments button on the game in the portal reads and posts comments on it. Reading needs no login. Posting uses the person's own GitHub token, so comments come from their account and can be moderated, edited or deleted here on GitHub. Issues must stay switched on for this repository.
