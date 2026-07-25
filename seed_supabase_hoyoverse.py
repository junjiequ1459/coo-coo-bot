import os
import zlib
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

GENSHIN_CHARACTERS = {
    "Aino": "https://static.wikia.nocookie.net/gensin-impact/images/3/3a/Aino_Character_Card.png/revision/latest?cb=20260408140035",
    "Albedo": "https://static.wikia.nocookie.net/gensin-impact/images/e/e4/Albedo_Character_Card.png/revision/latest?cb=20230917061858",
    "Alhaitham": "https://static.wikia.nocookie.net/gensin-impact/images/9/9b/Alhaitham_Character_Card.png/revision/latest?cb=20231221224755",
    "Aloy": "https://static.wikia.nocookie.net/gensin-impact/images/0/0f/Aloy_Wish.png/revision/latest?cb=20231214213630",
    "Amber": "https://static.wikia.nocookie.net/gensin-impact/images/8/89/Amber_Character_Card.png/revision/latest?cb=20230519022227",
    "Arataki Itto": "https://static.wikia.nocookie.net/gensin-impact/images/7/7d/Arataki_Itto_Character_Card.png/revision/latest?cb=20230415230222",
    "Arlecchino": "https://static.wikia.nocookie.net/gensin-impact/images/d/da/Arlecchino_Character_Card.png/revision/latest?cb=20250212015245",
    "Baizhu": "https://static.wikia.nocookie.net/gensin-impact/images/9/99/Baizhu_Character_Card.png/revision/latest?cb=20231112065812",
    "Barbara": "https://static.wikia.nocookie.net/gensin-impact/images/2/24/Barbara_Character_Card.png/revision/latest?cb=20221205102816",
    "Beidou": "https://static.wikia.nocookie.net/gensin-impact/images/2/2a/Beidou_Character_Card.png/revision/latest?cb=20230118044002",
    "Bennett": "https://static.wikia.nocookie.net/gensin-impact/images/a/a9/Bennett_Character_Card.png/revision/latest?cb=20221205102818",
    "Candace": "https://static.wikia.nocookie.net/gensin-impact/images/9/9e/Candace_Character_Card.png/revision/latest?cb=20230710005015",
    "Charlotte": "https://static.wikia.nocookie.net/gensin-impact/images/1/16/Charlotte_Character_Card.png/revision/latest?cb=20240313100716",
    "Chasca": "https://static.wikia.nocookie.net/gensin-impact/images/3/30/Chasca_Character_Card.png/revision/latest?cb=20250619164742",
    "Chevreuse": "https://static.wikia.nocookie.net/gensin-impact/images/6/61/Chevreuse_Character_Card.png/revision/latest?cb=20240717072430",
    "Chiori": "https://static.wikia.nocookie.net/gensin-impact/images/0/0c/Chiori_Character_Card.png/revision/latest?cb=20241009100219",
    "Chongyun": "https://static.wikia.nocookie.net/gensin-impact/images/6/64/Chongyun_Character_Card.png/revision/latest?cb=20221205102219",
    "Citlali": "https://static.wikia.nocookie.net/gensin-impact/images/4/41/Citlali_Character_Card.png/revision/latest?cb=20250619164757",
    "Clorinde": "https://static.wikia.nocookie.net/gensin-impact/images/f/f7/Clorinde_Character_Card.png/revision/latest?cb=20250101212730",
    "Collei": "https://static.wikia.nocookie.net/gensin-impact/images/e/e2/Collei_Character_Card.png/revision/latest?cb=20221205102224",
    "Columbina": "https://static.wikia.nocookie.net/gensin-impact/images/2/22/Columbina_Wish.png/revision/latest?cb=20260114052008",
    "Cyno": "https://static.wikia.nocookie.net/gensin-impact/images/1/1f/Cyno_Character_Card.png/revision/latest?cb=20221205102234",
    "Dahlia": "https://static.wikia.nocookie.net/gensin-impact/images/0/05/Dahlia_Character_Card.png/revision/latest?cb=20260408140028",
    "Dehya": "https://static.wikia.nocookie.net/gensin-impact/images/d/d7/Dehya_Character_Card.png/revision/latest?cb=20230929035950",
    "Diluc": "https://static.wikia.nocookie.net/gensin-impact/images/a/a7/Diluc_Character_Card.png/revision/latest?cb=20221205105853",
    "Diona": "https://static.wikia.nocookie.net/gensin-impact/images/3/31/Diona_Character_Card.png/revision/latest?cb=20221205102243",
    "Dori": "https://static.wikia.nocookie.net/gensin-impact/images/8/89/Dori_Character_Card.png/revision/latest?cb=20231112065833",
    "Durin": "https://static.wikia.nocookie.net/gensin-impact/images/a/a3/Durin_Wish.png/revision/latest?cb=20251204124550",
    "Emilie": "https://static.wikia.nocookie.net/gensin-impact/images/b/b3/Emilie_Character_Card.png/revision/latest?cb=20250326091822",
    "Escoffier": "https://static.wikia.nocookie.net/gensin-impact/images/2/21/Escoffier_Character_Card.png/revision/latest?cb=20251203144659",
    "Eula": "https://static.wikia.nocookie.net/gensin-impact/images/3/3a/Eula_Character_Card.png/revision/latest?cb=20230302031310",
    "Faruzan": "https://static.wikia.nocookie.net/gensin-impact/images/0/06/Faruzan_Character_Card.png/revision/latest?cb=20240425211827",
    "Fischl": "https://static.wikia.nocookie.net/gensin-impact/images/7/7d/Fischl_Character_Card.png/revision/latest?cb=20221205102329",
    "Flins": "https://static.wikia.nocookie.net/gensin-impact/images/2/26/Flins_Character_Card.png/revision/latest?cb=20260521141408",
    "Freminet": "https://static.wikia.nocookie.net/gensin-impact/images/5/50/Freminet_Character_Card.png/revision/latest?cb=20240828015834",
    "Furina": "https://static.wikia.nocookie.net/gensin-impact/images/a/ac/Furina_Character_Card.png/revision/latest?cb=20240528044514",
    "Gaming": "https://static.wikia.nocookie.net/gensin-impact/images/4/48/Gaming_Character_Card.png/revision/latest?cb=20250221110006",
    "Ganyu": "https://static.wikia.nocookie.net/gensin-impact/images/8/87/Ganyu_Character_Card.png/revision/latest?cb=20221205075636",
    "Gorou": "https://static.wikia.nocookie.net/gensin-impact/images/0/01/Gorou_Character_Card.png/revision/latest?cb=20231221225102",
    "Hu Tao": "https://static.wikia.nocookie.net/gensin-impact/images/9/90/Hu_Tao_Character_Card.png/revision/latest?cb=20230519022250",
    "Iansan": "https://static.wikia.nocookie.net/gensin-impact/images/b/be/Iansan_Character_Card.png/revision/latest?cb=20250911191755",
    "Ifa": "https://static.wikia.nocookie.net/gensin-impact/images/8/8d/Ifa_Character_Card.png/revision/latest?cb=20251022121708",
    "Illuga": "https://static.wikia.nocookie.net/gensin-impact/images/0/0f/Illuga_Wish.png/revision/latest?cb=20260205110314",
    "Ineffa": "https://static.wikia.nocookie.net/gensin-impact/images/d/d8/Ineffa_Character_Card.png/revision/latest?cb=20260225134914",
    "Jahoda": "https://static.wikia.nocookie.net/gensin-impact/images/3/36/Jahoda_Wish.png/revision/latest?cb=20260127111107",
    "Jean": "https://static.wikia.nocookie.net/gensin-impact/images/b/b0/Jean_Character_Card.png/revision/latest?cb=20221205102407",
    "Kachina": "https://static.wikia.nocookie.net/gensin-impact/images/a/a4/Kachina_Character_Card.png/revision/latest?cb=20250326091824",
    "Kaedehara Kazuha": "https://static.wikia.nocookie.net/gensin-impact/images/6/67/Kaedehara_Kazuha_Character_Card.png/revision/latest?cb=20230711013439",
    "Kaeya": "https://static.wikia.nocookie.net/gensin-impact/images/c/cd/Kaeya_Character_Card.png/revision/latest?cb=20221205102413",
    "Kamisato Ayaka": "https://static.wikia.nocookie.net/gensin-impact/images/7/72/Kamisato_Ayaka_Character_Card.png/revision/latest?cb=20221205102416",
    "Kamisato Ayato": "https://static.wikia.nocookie.net/gensin-impact/images/9/9e/Kamisato_Ayato_Character_Card.png/revision/latest?cb=20230415230237",
    "Kaveh": "https://static.wikia.nocookie.net/gensin-impact/images/c/c5/Kaveh_Character_Card.png/revision/latest?cb=20240528044438",
    "Keqing": "https://static.wikia.nocookie.net/gensin-impact/images/d/dd/Keqing_Character_Card.png/revision/latest?cb=20221205102425",
    "Kinich": "https://static.wikia.nocookie.net/gensin-impact/images/a/ae/Kinich_Character_Card.png/revision/latest?cb=20250212015300",
    "Kirara": "https://static.wikia.nocookie.net/gensin-impact/images/e/ec/Kirara_Character_Card.png/revision/latest?cb=20240313100730",
    "Klee": "https://static.wikia.nocookie.net/gensin-impact/images/d/d4/Klee_Character_Card.png/revision/latest?cb=20230118043948",
    "Kujou Sara": "https://static.wikia.nocookie.net/gensin-impact/images/8/84/Kujou_Sara_Character_Card.png/revision/latest?cb=20230302031244",
    "Kuki Shinobu": "https://static.wikia.nocookie.net/gensin-impact/images/e/e1/Kuki_Shinobu_Character_Card.png/revision/latest?cb=20240425213341",
    "Lan Yan": "https://static.wikia.nocookie.net/gensin-impact/images/b/b9/Lan_Yan_Character_Card.png/revision/latest?cb=20250730101106",
    "Lauma": "https://static.wikia.nocookie.net/gensin-impact/images/6/66/Lauma_Character_Card.png/revision/latest?cb=20260521141420",
    "Layla": "https://static.wikia.nocookie.net/gensin-impact/images/6/6f/Layla_Character_Card.png/revision/latest?cb=20231221225157",
    "Linnea": "https://static.wikia.nocookie.net/gensin-impact/images/d/da/Linnea_Wish.png/revision/latest?cb=20260408075929",
    "Lisa": "https://static.wikia.nocookie.net/gensin-impact/images/c/c3/Lisa_Character_Card.png/revision/latest?cb=20230917062042",
    "Lohen": "https://static.wikia.nocookie.net/gensin-impact/images/f/fe/Lohen_Wish.png/revision/latest?cb=20260609140934",
    "Lynette": "https://static.wikia.nocookie.net/gensin-impact/images/c/c7/Lynette_Character_Card.png/revision/latest?cb=20231221225249",
    "Lyney": "https://static.wikia.nocookie.net/gensin-impact/images/5/56/Lyney_Character_Card.png/revision/latest?cb=20231221225303",
    "Mavuika": "https://static.wikia.nocookie.net/gensin-impact/images/6/6c/Mavuika_Character_Card.png/revision/latest?cb=20250619164829",
    "Mika": "https://static.wikia.nocookie.net/gensin-impact/images/3/37/Mika_Character_Card.png/revision/latest?cb=20260225134905",
    "Mona": "https://static.wikia.nocookie.net/gensin-impact/images/c/cb/Mona_Character_Card.png/revision/latest?cb=20221205102511",
    "Mualani": "https://static.wikia.nocookie.net/gensin-impact/images/4/40/Mualani_Character_Card.png/revision/latest?cb=20250101212733",
    "Nahida": "https://static.wikia.nocookie.net/gensin-impact/images/c/c1/Nahida_Character_Card.png/revision/latest?cb=20230519022257",
    "Navia": "https://static.wikia.nocookie.net/gensin-impact/images/a/a6/Navia_Character_Card.png/revision/latest?cb=20240717072058",
    "Nefer": "https://static.wikia.nocookie.net/gensin-impact/images/1/16/Nefer_Character_Card.png/revision/latest?cb=20260701185644",
    "Neuvillette": "https://static.wikia.nocookie.net/gensin-impact/images/7/71/Neuvillette_Character_Card.png/revision/latest?cb=20240313100724",
    "Nicole": "https://static.wikia.nocookie.net/gensin-impact/images/6/6c/Nicole_Wish.png/revision/latest?cb=20260520063741",
    "Nilou": "https://static.wikia.nocookie.net/gensin-impact/images/6/6d/Nilou_Character_Card.png/revision/latest?cb=20231112065859",
    "Ningguang": "https://static.wikia.nocookie.net/gensin-impact/images/9/93/Ningguang_Character_Card.png/revision/latest?cb=20221205102523",
    "Noelle": "https://static.wikia.nocookie.net/gensin-impact/images/d/d6/Noelle_Character_Card.png/revision/latest?cb=20221205102528",
    "Ororon": "https://static.wikia.nocookie.net/gensin-impact/images/8/8e/Ororon_Character_Card.png/revision/latest?cb=20260114203031",
    "Prune": "https://static.wikia.nocookie.net/gensin-impact/images/a/ae/Prune_Wish.png/revision/latest?cb=20260520080122",
    "Qiqi": "https://static.wikia.nocookie.net/gensin-impact/images/1/1e/Qiqi_Character_Card.png/revision/latest?cb=20230917062114",
    "Raiden Shogun": "https://static.wikia.nocookie.net/gensin-impact/images/c/c9/Raiden_Shogun_Character_Card.png/revision/latest?cb=20230519022303",
    "Razor": "https://static.wikia.nocookie.net/gensin-impact/images/2/27/Razor_Character_Card.png/revision/latest?cb=20221205102556",
    "Rosaria": "https://static.wikia.nocookie.net/gensin-impact/images/8/88/Rosaria_Character_Card.png/revision/latest?cb=20241127142842",
    "Sandrone": "https://static.wikia.nocookie.net/gensin-impact/images/4/41/Sandrone_Wish.png/revision/latest?cb=20260701022155",
    "Sangonomiya Kokomi": "https://static.wikia.nocookie.net/gensin-impact/images/d/d3/Sangonomiya_Kokomi_Character_Card.png/revision/latest?cb=20230302031258",
    "Sayu": "https://static.wikia.nocookie.net/gensin-impact/images/0/0d/Sayu_Character_Card.png/revision/latest?cb=20240131103512",
    "Sethos": "https://static.wikia.nocookie.net/gensin-impact/images/b/b3/Sethos_Character_Card.png/revision/latest?cb=20250507153757",
    "Shenhe": "https://static.wikia.nocookie.net/gensin-impact/images/c/ca/Shenhe_Character_Card.png/revision/latest?cb=20230519022309",
    "Shikanoin Heizou": "https://static.wikia.nocookie.net/gensin-impact/images/5/54/Shikanoin_Heizou_Character_Card.png/revision/latest?cb=20250730101025",
    "Sigewinne": "https://static.wikia.nocookie.net/gensin-impact/images/8/82/Sigewinne_Character_Card.png/revision/latest?cb=20241127142903",
    "Skirk": "https://static.wikia.nocookie.net/gensin-impact/images/7/75/Skirk_Character_Card.png/revision/latest?cb=20260114203029",
    "Sucrose": "https://static.wikia.nocookie.net/gensin-impact/images/4/42/Sucrose_Character_Card.png/revision/latest?cb=20221205102645",
    "Tartaglia": "https://static.wikia.nocookie.net/gensin-impact/images/d/d7/Tartaglia_Character_Card.png/revision/latest?cb=20230519022317",
    "Thoma": "https://static.wikia.nocookie.net/gensin-impact/images/1/19/Thoma_Character_Card.png/revision/latest?cb=20240131104004",
    "Tighnari": "https://static.wikia.nocookie.net/gensin-impact/images/2/24/Tighnari_Character_Card.png/revision/latest?cb=20230415230207",
    "Varesa": "https://static.wikia.nocookie.net/gensin-impact/images/6/67/Varesa_Character_Card.png/revision/latest?cb=20251022121710",
    "Varka": "https://static.wikia.nocookie.net/gensin-impact/images/8/85/Varka_Wish.png/revision/latest?cb=20260225074015",
    "Venti": "https://static.wikia.nocookie.net/gensin-impact/images/4/4a/Venti_Character_Card.png/revision/latest?cb=20230519022324",
    "Wanderer": "https://static.wikia.nocookie.net/gensin-impact/images/8/86/Wanderer_Character_Card.png/revision/latest?cb=20231028173220",
    "Wriothesley": "https://static.wikia.nocookie.net/gensin-impact/images/b/b8/Wriothesley_Character_Card.png/revision/latest?cb=20240528044505",
    "Xiangling": "https://static.wikia.nocookie.net/gensin-impact/images/2/2a/Xiangling_Character_Card.png/revision/latest?cb=20221205102755",
    "Xianyun": "https://static.wikia.nocookie.net/gensin-impact/images/0/06/Xianyun_Character_Card.png/revision/latest?cb=20240828015945",
    "Xiao": "https://static.wikia.nocookie.net/gensin-impact/images/c/c1/Xiao_Character_Card.png/revision/latest?cb=20230519022329",
    "Xilonen": "https://static.wikia.nocookie.net/gensin-impact/images/8/8e/Xilonen_Character_Card.png/revision/latest?cb=20250507153819",
    "Xingqiu": "https://static.wikia.nocookie.net/gensin-impact/images/f/f9/Xingqiu_Character_Card.png/revision/latest?cb=20221205102757",
    "Xinyan": "https://static.wikia.nocookie.net/gensin-impact/images/1/18/Xinyan_Character_Card.png/revision/latest?cb=20240528044507",
    "Yae Miko": "https://static.wikia.nocookie.net/gensin-impact/images/2/2c/Yae_Miko_Character_Card.png/revision/latest?cb=20230519022337",
    "Yanfei": "https://static.wikia.nocookie.net/gensin-impact/images/7/76/Yanfei_Character_Card.png/revision/latest?cb=20230711013455",
    "Yaoyao": "https://static.wikia.nocookie.net/gensin-impact/images/c/cd/Yaoyao_Character_Card.png/revision/latest?cb=20230929040019",
    "Yelan": "https://static.wikia.nocookie.net/gensin-impact/images/a/a8/Yelan_Character_Card.png/revision/latest?cb=20231221225634",
    "Yoimiya": "https://static.wikia.nocookie.net/gensin-impact/images/9/98/Yoimiya_Character_Card.png/revision/latest?cb=20221205102802",
    "Yumemizuki Mizuki": "https://static.wikia.nocookie.net/gensin-impact/images/c/c3/Yumemizuki_Mizuki_Character_Card.png/revision/latest?cb=20250911191737",
    "Yun Jin": "https://static.wikia.nocookie.net/gensin-impact/images/1/17/Yun_Jin_Character_Card.png/revision/latest?cb=20240528044509",
    "Zhongli": "https://static.wikia.nocookie.net/gensin-impact/images/0/02/Zhongli_Character_Card.png/revision/latest?cb=20230519022344",
    "Zibai": "https://static.wikia.nocookie.net/gensin-impact/images/0/0b/Zibai_Wish.png/revision/latest?cb=20260205111420"
}

HSR_CHARACTERS = {
    "Acheron": "https://starrail.honeyhunterworld.com/img/character/acheron-character_gacha_result_bg.webp",
    "Aglaea": "https://starrail.honeyhunterworld.com/img/character/aglaea-character_gacha_result_bg.webp",
    "Anaxa": "https://starrail.honeyhunterworld.com/img/character/anaxa-character_gacha_result_bg.webp",
    "Archer": "https://starrail.honeyhunterworld.com/img/character/archer-character_gacha_result_bg.webp",
    "Argenti": "https://starrail.honeyhunterworld.com/img/character/argenti-character_gacha_result_bg.webp",
    "Arlan": "https://starrail.honeyhunterworld.com/img/character/arlan-character_gacha_result_bg.webp",
    "Ashveil": "https://starrail.honeyhunterworld.com/img/character/ashveil-character_gacha_result_bg.webp",
    "Asta": "https://starrail.honeyhunterworld.com/img/character/asta-character_gacha_result_bg.webp",
    "Aventurine": "https://starrail.honeyhunterworld.com/img/character/aventurine-character_gacha_result_bg.webp",
    "Aventurine Waveflair": "https://starrail.honeyhunterworld.com/img/character/aventurine-waveflair-character_gacha_result_bg.webp",
    "Bailu": "https://starrail.honeyhunterworld.com/img/character/bailu-character_gacha_result_bg.webp",
    "Black Swan": "https://starrail.honeyhunterworld.com/img/character/black-swan-character_gacha_result_bg.webp",
    "Blade": "https://starrail.honeyhunterworld.com/img/character/blade-character_gacha_result_bg.webp",
    "Boothill": "https://starrail.honeyhunterworld.com/img/character/boothill-character_gacha_result_bg.webp",
    "Bronya": "https://starrail.honeyhunterworld.com/img/character/bronya-character_gacha_result_bg.webp",
    "Castorice": "https://starrail.honeyhunterworld.com/img/character/castorice-character_gacha_result_bg.webp",
    "Cerydra": "https://starrail.honeyhunterworld.com/img/character/cerydra-character_gacha_result_bg.webp",
    "Cipher": "https://starrail.honeyhunterworld.com/img/character/cipher-character_gacha_result_bg.webp",
    "Clara": "https://starrail.honeyhunterworld.com/img/character/clara-character_gacha_result_bg.webp",
    "Cyrene": "https://starrail.honeyhunterworld.com/img/character/cyrene-character_gacha_result_bg.webp",
    "Dan Heng": "https://starrail.honeyhunterworld.com/img/character/dan-heng-character_gacha_result_bg.webp",
    "Dan Heng \u2022 Imbibitor Lunae": "https://starrail.honeyhunterworld.com/img/character/dan-heng-imbibitor-lunae-character_gacha_result_bg.webp",
    "Dan Heng \u2022 Permansor Terrae": "https://starrail.honeyhunterworld.com/img/character/dan-heng-permansor-terrae-character_gacha_result_bg.webp",
    "Dr. Ratio": "https://starrail.honeyhunterworld.com/img/character/dr-ratio-character_gacha_result_bg.webp",
    "Evanescia": "https://starrail.honeyhunterworld.com/img/character/evanescia-character_gacha_result_bg.webp",
    "Feixiao": "https://starrail.honeyhunterworld.com/img/character/feixiao-character_gacha_result_bg.webp",
    "Firefly": "https://starrail.honeyhunterworld.com/img/character/firefly-character_gacha_result_bg.webp",
    "Fu Xuan": "https://starrail.honeyhunterworld.com/img/character/fu-xuan-character_gacha_result_bg.webp",
    "Gallagher": "https://starrail.honeyhunterworld.com/img/character/gallagher-character_gacha_result_bg.webp",
    "Gepard": "https://starrail.honeyhunterworld.com/img/character/gepard-character_gacha_result_bg.webp",
    "Gilgamesh": "https://starrail.honeyhunterworld.com/img/character/gilgamesh-character_gacha_result_bg.webp",
    "Guinaifen": "https://starrail.honeyhunterworld.com/img/character/guinaifen-character_gacha_result_bg.webp",
    "Hanya": "https://starrail.honeyhunterworld.com/img/character/hanya-character_gacha_result_bg.webp",
    "Herta": "https://starrail.honeyhunterworld.com/img/character/herta-character_gacha_result_bg.webp",
    "Himeko": "https://starrail.honeyhunterworld.com/img/character/himeko-character_gacha_result_bg.webp",
    "Himeko Nova": "https://starrail.honeyhunterworld.com/img/character/himeko-nova-character_gacha_result_bg.webp",
    "Hook": "https://starrail.honeyhunterworld.com/img/character/hook-character_gacha_result_bg.webp",
    "Huohuo": "https://starrail.honeyhunterworld.com/img/character/huohuo-character_gacha_result_bg.webp",
    "Hyacine": "https://starrail.honeyhunterworld.com/img/character/hyacine-character_gacha_result_bg.webp",
    "Hysilens": "https://starrail.honeyhunterworld.com/img/character/hysilens-character_gacha_result_bg.webp",
    "Jade": "https://starrail.honeyhunterworld.com/img/character/jade-character_gacha_result_bg.webp",
    "Jiaoqiu": "https://starrail.honeyhunterworld.com/img/character/jiaoqiu-character_gacha_result_bg.webp",
    "Jing Yuan": "https://starrail.honeyhunterworld.com/img/character/jing-yuan-character_gacha_result_bg.webp",
    "Jingliu": "https://starrail.honeyhunterworld.com/img/character/jingliu-character_gacha_result_bg.webp",
    "Kafka": "https://starrail.honeyhunterworld.com/img/character/kafka-character_gacha_result_bg.webp",
    "Lingsha": "https://starrail.honeyhunterworld.com/img/character/lingsha-character_gacha_result_bg.webp",
    "Luka": "https://starrail.honeyhunterworld.com/img/character/luka-character_gacha_result_bg.webp",
    "Luocha": "https://starrail.honeyhunterworld.com/img/character/luocha-character_gacha_result_bg.webp",
    "Lynx": "https://starrail.honeyhunterworld.com/img/character/lynx-character_gacha_result_bg.webp",
    "March 7th": "https://starrail.honeyhunterworld.com/img/character/march-7th-character_gacha_result_bg.webp",
    "March 7th \u2022 Evernight": "https://starrail.honeyhunterworld.com/img/character/march-7th-evernight-character_gacha_result_bg.webp",
    "March 7th \u2022 The Hunt": "https://starrail.honeyhunterworld.com/img/character/march-7th-the-hunt-character_gacha_result_bg.webp",
    "Misha": "https://starrail.honeyhunterworld.com/img/character/misha-character_gacha_result_bg.webp",
    "Mortenax Blade": "https://starrail.honeyhunterworld.com/img/character/mortenax-blade-character_gacha_result_bg.webp",
    "Moze": "https://starrail.honeyhunterworld.com/img/character/moze-character_gacha_result_bg.webp",
    "Mydei": "https://starrail.honeyhunterworld.com/img/character/mydei-character_gacha_result_bg.webp",
    "Natasha": "https://starrail.honeyhunterworld.com/img/character/natasha-character_gacha_result_bg.webp",
    "Pela": "https://starrail.honeyhunterworld.com/img/character/pela-character_gacha_result_bg.webp",
    "Phainon": "https://starrail.honeyhunterworld.com/img/character/phainon-character_gacha_result_bg.webp",
    "Qingque": "https://starrail.honeyhunterworld.com/img/character/qingque-character_gacha_result_bg.webp",
    "Rappa": "https://starrail.honeyhunterworld.com/img/character/rappa-character_gacha_result_bg.webp",
    "Rin Tohsaka": "https://starrail.honeyhunterworld.com/img/character/rin-tohsaka-character_gacha_result_bg.webp",
    "Robin": "https://starrail.honeyhunterworld.com/img/character/robin-character_gacha_result_bg.webp",
    "Robin Summeretto": "https://starrail.honeyhunterworld.com/img/character/robin-summeretto-character_gacha_result_bg.webp",
    "Ruan Mei": "https://starrail.honeyhunterworld.com/img/character/ruan-mei-character_gacha_result_bg.webp",
    "Saber": "https://starrail.honeyhunterworld.com/img/character/saber-character_gacha_result_bg.webp",
    "Sampo": "https://starrail.honeyhunterworld.com/img/character/sampo-character_gacha_result_bg.webp",
    "Seele": "https://starrail.honeyhunterworld.com/img/character/seele-character_gacha_result_bg.webp",
    "Serval": "https://starrail.honeyhunterworld.com/img/character/serval-character_gacha_result_bg.webp",
    "Silver Wolf": "https://starrail.honeyhunterworld.com/img/character/silver-wolf-character_gacha_result_bg.webp",
    "Silver Wolf \u2022 Lv. 999": "https://starrail.honeyhunterworld.com/img/character/silver-wolf-lv-999-character_gacha_result_bg.webp",
    "Sparkle": "https://starrail.honeyhunterworld.com/img/character/sparkle-character_gacha_result_bg.webp",
    "Sparxie": "https://starrail.honeyhunterworld.com/img/character/sparxie-character_gacha_result_bg.webp",
    "Sunday": "https://starrail.honeyhunterworld.com/img/character/sunday-character_gacha_result_bg.webp",
    "Sushang": "https://starrail.honeyhunterworld.com/img/character/sushang-character_gacha_result_bg.webp",
    "The Dahlia": "https://starrail.honeyhunterworld.com/img/character/the-dahlia-character_gacha_result_bg.webp",
    "The Herta": "https://starrail.honeyhunterworld.com/img/character/the-herta-character_gacha_result_bg.webp",
    "Tingyun": "https://starrail.honeyhunterworld.com/img/character/tingyun-character_gacha_result_bg.webp",
    "Fugue": "https://starrail.honeyhunterworld.com/img/character/fugue-character_gacha_result_bg.webp",
    "Topaz & Numby": "https://starrail.honeyhunterworld.com/img/character/topaz-numby-character_gacha_result_bg.webp",
    "Trailblazer \u2022 Destruction": "https://starrail.honeyhunterworld.com/img/character/trailblazer-destruction-male-character_gacha_result_bg.webp",
    "Trailblazer \u2022 Elation": "https://starrail.honeyhunterworld.com/img/character/trailblazer-elation-male-character_gacha_result_bg.webp",
    "Trailblazer \u2022 Harmony": "https://starrail.honeyhunterworld.com/img/character/trailblazer-harmony-male-character_gacha_result_bg.webp",
    "Trailblazer \u2022 Preservation": "https://starrail.honeyhunterworld.com/img/character/trailblazer-preservation-male-character_gacha_result_bg.webp",
    "Trailblazer \u2022 Remembrance": "https://starrail.honeyhunterworld.com/img/character/trailblazer-remembrance-male-character_gacha_result_bg.webp",
    "Tribbie": "https://starrail.honeyhunterworld.com/img/character/tribbie-character_gacha_result_bg.webp",
    "Welt": "https://starrail.honeyhunterworld.com/img/character/welt-character_gacha_result_bg.webp",
    "Xueyi": "https://starrail.honeyhunterworld.com/img/character/xueyi-character_gacha_result_bg.webp",
    "Yanqing": "https://starrail.honeyhunterworld.com/img/character/yanqing-character_gacha_result_bg.webp",
    "Yao Guang": "https://starrail.honeyhunterworld.com/img/character/yao-guang-character_gacha_result_bg.webp",
    "Yukong": "https://starrail.honeyhunterworld.com/img/character/yukong-character_gacha_result_bg.webp",
    "Yunli": "https://starrail.honeyhunterworld.com/img/character/yunli-character_gacha_result_bg.webp"
}

HSR_CHAR_NAMES = [
    "Acheron",
    "Aglaea",
    "Anaxa",
    "Archer",
    "Argenti",
    "Arlan",
    "Ashveil",
    "Asta",
    "Aventurine",
    "Aventurine Waveflair",
    "Bailu",
    "Black Swan",
    "Blade",
    "Boothill",
    "Bronya",
    "Castorice",
    "Cerydra",
    "Cipher",
    "Clara",
    "Cyrene",
    "Dan Heng",
    "Dan Heng \u2022 Imbibitor Lunae",
    "Dan Heng \u2022 Permansor Terrae",
    "Dr. Ratio",
    "Evanescia",
    "Feixiao",
    "Firefly",
    "Fu Xuan",
    "Gallagher",
    "Gepard",
    "Gilgamesh",
    "Guinaifen",
    "Hanya",
    "Herta",
    "Himeko",
    "Himeko Nova",
    "Hook",
    "Huohuo",
    "Hyacine",
    "Hysilens",
    "Jade",
    "Jiaoqiu",
    "Jing Yuan",
    "Jingliu",
    "Kafka",
    "Lingsha",
    "Luka",
    "Luocha",
    "Lynx",
    "March 7th",
    "March 7th \u2022 Evernight",
    "March 7th \u2022 The Hunt",
    "Misha",
    "Mortenax Blade",
    "Moze",
    "Mydei",
    "Natasha",
    "Pela",
    "Phainon",
    "Qingque",
    "Rappa",
    "Rin Tohsaka",
    "Robin",
    "Robin Summeretto",
    "Ruan Mei",
    "Saber",
    "Sampo",
    "Seele",
    "Serval",
    "Silver Wolf",
    "Silver Wolf \u2022 Lv. 999",
    "Sparkle",
    "Sparxie",
    "Sunday",
    "Sushang",
    "The Dahlia",
    "The Herta",
    "Tingyun",
    "Fugue",
    "Topaz & Numby",
    "Trailblazer \u2022 Destruction",
    "Trailblazer \u2022 Elation",
    "Trailblazer \u2022 Harmony",
    "Trailblazer \u2022 Preservation",
    "Trailblazer \u2022 Remembrance",
    "Tribbie",
    "Welt",
    "Xueyi",
    "Yanqing",
    "Yao Guang",
    "Yukong",
    "Yunli"
]

LOW_RARITY_HINTS = {'Amber', 'Kaeya', 'Lisa', 'Barbara', 'Razor', 'Xiangling', 'Beidou', 'Xingqiu', 'Ningguang', 'Fischl', 'Bennett', 'Noelle', 'Chongyun', 'Sucrose', 'Diona', 'Xinyan', 'Rosaria', 'Yanfei', 'Sayu', 'Kujou Sara', 'Thoma', 'Gorou', 'Yun Jin', 'Kuki Shinobu', 'Heizou', 'Collei', 'Dori', 'Candace', 'Layla', 'Faruzan', 'Yaoyao', 'Kaveh', 'Kirara', 'Lynette', 'Freminet', 'Charlotte', 'Chevreuse', 'Gaming', 'Sethos', 'Kachina', 'Ororon', 'Iansan', 'Arlan', 'Asta', 'Herta', 'Serval', 'Natasha', 'Pela', 'Sampo', 'Hook', 'Qingque', 'Tingyun', 'Sushang', 'Yukong', 'Luka', 'Lynx', 'Guinaifen', 'Hanya', 'Xueyi', 'Misha', 'Gallagher', 'Moze'}

def seed_database():
    if not DATABASE_URL:
        print("❌ DATABASE_URL missing!")
        return

    print("🔌 Connecting to Supabase PostgreSQL database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards_pool (
        id SERIAL PRIMARY KEY,
        anilist_id INTEGER UNIQUE,
        character_name TEXT NOT NULL,
        series_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        favourites INTEGER DEFAULT 0,
        rarity TEXT NOT NULL
    )
    ''')
    conn.commit()

    # Clean up misclassified characters from previous runs
    cursor.execute("DELETE FROM cards_pool WHERE anilist_id IN (126824, 335476, 13580, 14771, 174356, 263449)")
    conn.commit()

    total_inserted = 0

    # 1. Genshin Characters (116 total)
    print(f"🎮 Seeding {len(GENSHIN_CHARACTERS)} Genshin Impact characters...")
    for name, img_url in GENSHIN_CHARACTERS.items():
        anilist_id = 9910000 + zlib.crc32(name.encode('utf-8')) % 100000
        rarity = "Rare" if name in LOW_RARITY_HINTS else "Legendary"
        favs = 3000 if rarity == "Rare" else 12000

        cursor.execute('''
        INSERT INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (anilist_id) DO UPDATE SET
            character_name = EXCLUDED.character_name,
            series_name = EXCLUDED.series_name,
            image_url = EXCLUDED.image_url,
            favourites = EXCLUDED.favourites,
            rarity = EXCLUDED.rarity
        ''', (anilist_id, name, "Genshin Impact", img_url, favs, rarity))
        total_inserted += 1

    # 2. Honkai: Star Rail Characters (using Light Cone artwork from Prydwen CDN)
    # Clean up any duplicate HSR characters that may have been added by other scripts (e.g. populate_all_series.py)
    # Our HSR anilist_ids are in the 9920000-9999999 range; remove any HSR entries outside that range
    cursor.execute("""
        DELETE FROM cards_pool 
        WHERE series_name ILIKE '%Honkai%Star%Rail%' 
        AND (anilist_id < 9920000 OR anilist_id > 9999999)
    """)
    # Also remove old HSR entries with non-Prydwen image URLs (duplicates from previous hash seeds)
    cursor.execute("""
        DELETE FROM cards_pool 
        WHERE series_name = 'Honkai: Star Rail' 
        AND image_url NOT LIKE 'https://starrail.honeyhunterworld.com/%%'
    """)
    conn.commit()
    print(f"🧹 Cleaned up duplicate HSR entries from other sources.")

    print(f"🎮 Seeding {len(HSR_CHAR_NAMES)} Honkai: Star Rail characters (using Light Cone artwork)...")
    for name in HSR_CHAR_NAMES:
        img_url = HSR_CHARACTERS.get(name)
        if not img_url:
            c_clean = name.replace(' • ', '_').replace(' & ', '_and_').replace('.', '').replace(':', '').replace(' ', '_')
            img_url = f"https://static.wikia.nocookie.net/houkai-star-rail/images/8/80/Character_{c_clean}_Splash_Art.png"

        anilist_id = 9920000 + zlib.crc32(name.encode('utf-8')) % 100000
        rarity = "Rare" if name in LOW_RARITY_HINTS or name in ['March 7th', 'Welt', 'Himeko', 'Arlan', 'Asta', 'Hook', 'Natasha', 'Misha', 'Sushang', 'Yukong'] else "Legendary"
        favs = 3000 if rarity == "Rare" else 12000

        cursor.execute('''
        INSERT INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (anilist_id) DO UPDATE SET
            character_name = EXCLUDED.character_name,
            series_name = EXCLUDED.series_name,
            image_url = EXCLUDED.image_url,
            favourites = EXCLUDED.favourites,
            rarity = EXCLUDED.rarity
        ''', (anilist_id, name, "Honkai: Star Rail", img_url, favs, rarity))
        total_inserted += 1

    conn.commit()

    cursor.execute("SELECT series_name, COUNT(*) FROM cards_pool WHERE series_name IN ('Genshin Impact', 'Honkai: Star Rail') GROUP BY series_name")
    summary = cursor.fetchall()
    print("\n✅ Complete Hoyoverse Seeding Finished! Final Counts in Supabase:")
    for series, count in summary:
        print(f"  - {series}: {count} cards")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    seed_database()
