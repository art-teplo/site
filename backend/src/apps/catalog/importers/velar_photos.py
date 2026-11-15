"""Фото Velar с velarwh.ru (решение № 166): студийное превью модели со
страницы дизайн-радиаторов и 2–3 интерьерных рендера со страницы модели.
Отобраны вручную по превью: по одному кадру на цвет, без крупных планов.
Белый — RAL 9016, чёрный — RAL 9005; красный — без привязки (его нет в
палитре серий). RT2W на сайте нет — фото нет."""

VELAR = 'https://velarwh.ru/m/5bb100f9bb750422e7f0ec51cfde2cd4/'
# (файл, положение, p — товар / i — интерьер, цвет: W, B, R или пусто)
VELAR_PHOTOS = {
    'velar-p200': [
        ('61becb0823794cf683e55f050fc8aa12.jpg', 'h', 'p', ''),
        ('67930d4ba9d1c41e89b9d230e10ff33e.jpg', 'h', 'p', 'B'),
    ],
    'velar-p30': [
        ('26c3229f1fc0f881f47c1415bda8f6aa.jpg', 'h', 'p', ''),
        ('042deb7891f99916f7f63c704bd7c5e3.jpg', 'h', 'i', 'R'),
        ('ef3d9ba371a4acc86df1691a615c0ba0.jpg', 'h', 'i', 'B'),
        ('73d5baa9a630b2b4c8da7271ae068cbd.jpg', 'v', 'p', ''),
        ('ab9909aae8c08a1407feecbc0d57a392.jpg', 'v', 'i', 'W'),
        ('5a223cd920f96a3e0a402835ae2a3e14.jpg', 'v', 'i', 'B'),
        ('5fe6431f84b131a9bdd939334565db32.jpg', 'v', 'i', 'R'),
    ],
    'velar-p300': [
        ('9b05314bda40de01ae136908fb5d22e2.jpg', 'h', 'p', ''),
        ('337c65ff8e5417b9cc2c9658d6b81d5f.jpg', 'h', 'p', ''),
    ],
    'velar-p60': [
        ('9cdc5dec81ecde316e6e09247af592e4.jpg', 'h', 'p', ''),
        ('cd68b4689de94beb6b272275dc5380fc.jpg', 'h', 'i', 'W'),
        ('f3bb161bfd43280eca271554ab5bb19b.jpg', 'h', 'i', 'R'),
        ('e0ca96883f7644cf251a28b9908d6290.jpg', 'v', 'p', ''),
        ('6dc236dcf423064fcce9c39898b15b09.jpg', 'v', 'i', 'W'),
        ('5e395c8279ca7dfcf8e3a4499209e841.jpg', 'v', 'i', 'B'),
        ('febd6e451624e56292bf18a544ee272d.jpg', 'v', 'i', 'R'),
    ],
    'velar-q40': [
        ('20745824132d3816ee92200970600ddc.jpg', 'v', 'p', ''),
        ('89a8fb8457e82b48e75ce721093c8de0.jpg', 'v', 'i', 'W'),
        ('4e46d009b7f390c61b2d3cfea271be76.jpg', 'v', 'i', 'B'),
    ],
    'velar-q500': [
        ('6f466443f4472cfc13bda997368bb012.jpg', 'h', 'p', ''),
        ('a7ee39d4c22b94507fa4f90aea71a52e.jpg', 'h', 'i', 'W'),
        ('654d4b121eeda4ed3c36ffad3e4e6aac.jpg', 'h', 'i', 'B'),
        ('359d9c3ccea99978b28cd9812584ae21.jpg', 'h', 'i', 'R'),
    ],
    'velar-q60': [
        ('aa46223f322e24d1afa75acabd8a0c55.jpg', 'h', 'p', ''),
        ('02002e934b6f726fe827d9b0e0c425b1.jpg', 'h', 'i', 'W'),
        ('8178c9a9f30fb5e85c6eafcf4cba2787.jpg', 'v', 'p', ''),
        ('e6564154c292da2219af1c35177434b0.jpg', 'v', 'i', 'W'),
        ('986cca8a81fd90bfe152d1076a4ab014.jpg', 'v', 'i', ''),
    ],
    'velar-q80': [
        ('abaeacc2eb124143dd88e3a44ba96360.jpg', 'h', 'p', ''),
        ('fe46ebac21cb3d9192fb376ec40a2af1.jpg', 'h', 'i', 'W'),
        ('bb28f869f17ae74c1e6f747f268ce017.jpg', 'h', 'i', 'B'),
        ('acd9e42e543ac62a2f32d26af3e6fdb3.jpg', 'h', 'i', 'R'),
        ('13e7dc9bd15b4bedf1bc67bf02f43b06.jpg', 'v', 'p', ''),
        ('414f72de57f27f73b4a0132cd41b12b4.jpg', 'v', 'i', 'W'),
        ('a739c39f7e4f541af3827e93315b7ee2.jpg', 'v', 'i', 'B'),
        ('3118357eb94eaf3b9c9e9993bb1eaeb6.jpg', 'v', 'i', 'R'),
    ],
    'velar-qt1': [
        ('ffca4ed3ff4bfa20ca979bdbcb46b3dd.jpg', 'v', 'p', ''),
        ('3650366cd119b2d90395cafabaede0ac.jpg', 'v', 'i', 'W'),
        ('59cb0f4818beaf8f48529b740f7c45ea.jpg', 'v', 'i', 'B'),
        ('5247d744c94deebcc522bfaca90b1bd8.jpg', 'v', 'i', 'R'),
    ],
    'velar-qt2': [
        ('a2798d68e8adbdd40c30ffd347e52b39.jpg', 'v', 'p', ''),
        ('40786091e5e99c126a0074bb4d801756.jpg', 'v', 'i', 'W'),
        ('85d6cdd26d193b78401f2e68a657647b.jpg', 'v', 'i', 'B'),
        ('f42892eb261ee38be04ea758ba9a09b9.jpg', 'v', 'i', 'R'),
    ],
    'velar-r32': [
        ('96b3032fa7a38afcce2ac3d08522e3ea.jpg', 'h', 'p', ''),
        ('46877b63e6c330265d5338d3829540ba.jpg', 'h', 'i', 'W'),
        ('9015b65e52e3de66d7c7c060bc1f99ac.jpg', 'h', 'i', 'B'),
        ('39a041bc45c9458069d08e75e2a7d32d.jpg', 'v', 'p', ''),
        ('7cd85bed9ccecda79c2d57f6889ed0ea.jpg', 'v', 'i', 'W'),
        ('786ffdb5d0f281837c236b57347cd7c6.jpg', 'v', 'i', 'R'),
    ],
    'velar-r42': [
        ('d70883fca942d0bd253118f6b7542064.jpg', 'h', 'p', ''),
        ('d94188de9950628475ae14899ccc0951.jpg', 'v', 'p', ''),
    ],
    'velar-r89': [
        ('df14374e21c7d93b7f4c9488bfe1b577.jpg', 'h', 'p', ''),
        ('ac351494918ea95858e171e9e792e7c2.jpg', 'h', 'i', 'W'),
        ('7deb3775c36adb4890e8ed974dca5dbd.jpg', 'h', 'i', 'B'),
        ('50772bb30a9f129c964b6f1e9f4a4365.jpg', 'h', 'i', 'R'),
        ('09f80c68b806fc8e568e0ea07fc5be6f.jpg', 'v', 'p', ''),
        ('025e0956eab85d16355fb7e21ffe83f1.jpg', 'v', 'i', 'W'),
        ('747abac2f2783166032a6eb4a0fae498.jpg', 'v', 'i', 'B'),
        ('ffd94be1f0378c5300e5d7cb5c5c4cf2.jpg', 'v', 'i', 'R'),
    ],
    'velar-rt1': [
        ('2113b1bc605c70d156ac6bfbdd5a15fe.jpg', 'v', 'p', ''),
        ('f275809f9aa03570380d7092e752f395.jpg', 'v', 'i', 'W'),
        ('bb1a42e4023b344096df276e9f861b66.jpg', 'v', 'i', 'B'),
        ('e4d23006e4534821ba1ec005f91b92c0.jpg', 'v', 'i', 'R'),
    ],
    'velar-rt1w': [
        ('19e8a87ccd0b0fb665c01cb7ce0c0600.jpg', 'v', 'p', ''),
        ('f275809f9aa03570380d7092e752f395.jpg', 'v', 'i', 'W'),
        ('bb1a42e4023b344096df276e9f861b66.jpg', 'v', 'i', 'B'),
        ('e4d23006e4534821ba1ec005f91b92c0.jpg', 'v', 'i', 'R'),
    ],
    'velar-rt2': [
        ('e3ea8df9d45af566c068074d2b5a1496.jpg', 'v', 'p', ''),
        ('a93fe128de257e55d80f18855fc4b48b.jpg', 'v', 'i', 'W'),
        ('67633dff9bf5668a132b3cb184db520e.jpg', 'v', 'i', 'B'),
        ('ff8163d2845eb14f31c762618f2c17c8.jpg', 'v', 'i', 'R'),
    ],
    'velar-s': [
        ('0b5b9ec41f1bfaa1b9d47d27cafb567a.jpg', 'h', 'p', ''),
        ('792c31f3e9df352e09a696816f4142d5.jpg', 'h', 'i', 'W'),
        ('631a07177724f3a223b6cfaf87ad1fbb.jpg', 'h', 'i', 'B'),
        ('8c06e88cef3a48b7467c67a345f9e742.jpg', 'h', 'i', 'R'),
        ('cd2394f5c95dd61ac39729b6dc8efec2.jpg', 'v', 'p', ''),
        ('565dcc39194dfda4d926a83505364328.jpg', 'v', 'i', 'W'),
        ('353fd3f771a066c742dca11c4085f359.jpg', 'v', 'i', 'B'),
        ('3f4f9612662b87841305d876ff04e814.jpg', 'v', 'i', 'R'),
    ],
    'velar-sp': [
        ('952dfba0c4b8588809e016cf66327288.jpg', 'h', 'p', ''),
        ('e49a0a8629d64124a3fce0b52eb829c0.jpg', 'h', 'i', 'B'),
        ('cb2c7e09dc939c3ae7944317235eb99f.jpg', 'h', 'i', 'R'),
        ('6d9d15c8ae5a3864ac89246ffcae8db4.jpg', 'v', 'p', ''),
        ('c068b8e2e901ee57c304457ea70c342c.jpg', 'v', 'i', 'W'),
        ('75a5d160309d1bc073628da22a96fb5b.jpg', 'v', 'i', 'B'),
        ('f3ba98244faaf5a2f9f8c5d3e06d4a1e.jpg', 'v', 'i', 'R'),
    ],
}
VELAR_COLORS = {'W': 'RAL 9016', 'B': 'RAL 9005'}
COLOR_WORD = {'W': 'белый', 'B': 'чёрный', 'R': 'красный'}
