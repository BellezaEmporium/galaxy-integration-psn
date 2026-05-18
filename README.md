## This applies fixes I found to a GitHub repo for simplicity. I claim none of this code.
- **This is simply a bandaid fix of the main repo, it is not meant to be a replacement for it. I'm not a maintainer, I can barely code. This is just what I know some of it may be incorrect.**

- This fork uses Playwright for logging in, which embarks a minimal edition of a web browser, hence the plugin size.

Supports PSN-owned game list & last played date. PSN API has changed several times over the last few years when this code was initially first created. [Several](https://github.com/andshrew/PlayStation-Trophies/blob/master/docs/APIv2.md) [trophy APIs](https://github.com/achievements-app/psn-api) have been created since then but they'd likely require nearly a full rewrite to be integrated into the GOG Galaxy integration.

## GOG Integration Levels
* Built-in Search: Yes, main repo only.
* Install & Launch: No, may be able to be reverse-engineered eventually via Remote Play API.
* Achievements: No, ever since the [discontinuation of My PlayStation](https://www.playstationlifestyle.net/2021/06/02/myplaystation-ps-vita-messaging-service-end/) back in 2021 achievements have been unsupported. Hopefully, they'll return one day.
* Game Time: Yes, only time last played.
* Friend Recommendation: No.
* Friend Presence: No.

## Credits

I've based this partially on work done by others:
* https://github.com/jhewt/gumer-psn
* https://github.com/Tustin/psn-php
* https://github.com/mgp25/psn-api
* https://github.com/adrianzhang/wechat-psn-backend
* https://github.com/FriendsOfGalaxy/galaxy-integration-psn
* https://github.com/Atlas1001/galaxy-integration-psn
