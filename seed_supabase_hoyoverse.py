import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

GENSHIN_CHARACTERS = {
    "Aino": "https://static.wikia.nocookie.net/gensin-impact/images/7/73/Aino_Wish.png/revision/latest?cb=20250910025417",
    "Albedo": "https://static.wikia.nocookie.net/gensin-impact/images/8/8f/Albedo_Wish.png/revision/latest?cb=20231214213308",
    "Alhaitham": "https://static.wikia.nocookie.net/gensin-impact/images/9/90/Alhaitham_Wish.png/revision/latest?cb=20231214213526",
    "Aloy": "https://static.wikia.nocookie.net/gensin-impact/images/0/0f/Aloy_Wish.png/revision/latest?cb=20231214213630",
    "Amber": "https://static.wikia.nocookie.net/gensin-impact/images/0/02/Amber_Wish.png/revision/latest?cb=20201119223905",
    "Arataki Itto": "https://static.wikia.nocookie.net/gensin-impact/images/b/b4/Arataki_Itto_Wish.png/revision/latest?cb=20231214214207",
    "Arlecchino": "https://static.wikia.nocookie.net/gensin-impact/images/7/7d/Arlecchino_Wish.png/revision/latest?cb=20240424055957",
    "Baizhu": "https://static.wikia.nocookie.net/gensin-impact/images/6/6b/Baizhu_Wish.png/revision/latest?cb=20231214214302",
    "Barbara": "https://static.wikia.nocookie.net/gensin-impact/images/1/1a/Barbara_Wish.png/revision/latest?cb=20231214214322",
    "Beidou": "https://static.wikia.nocookie.net/gensin-impact/images/3/33/Beidou_Wish.png/revision/latest?cb=20231214214414",
    "Bennett": "https://static.wikia.nocookie.net/gensin-impact/images/8/88/Bennett_Wish.png/revision/latest?cb=20231214214450",
    "Candace": "https://static.wikia.nocookie.net/gensin-impact/images/0/01/Candace_Wish.png/revision/latest?cb=20231214214525",
    "Charlotte": "https://static.wikia.nocookie.net/gensin-impact/images/5/5b/Charlotte_Wish.png/revision/latest?cb=20231108031307",
    "Chasca": "https://static.wikia.nocookie.net/gensin-impact/images/d/d4/Chasca_Wish.png/revision/latest?cb=20241120030619",
    "Chevreuse": "https://static.wikia.nocookie.net/gensin-impact/images/2/2f/Chevreuse_Wish.png/revision/latest?cb=20240109210200",
    "Chiori": "https://static.wikia.nocookie.net/gensin-impact/images/9/9e/Chiori_Wish.png/revision/latest?cb=20240313020133",
    "Chongyun": "https://static.wikia.nocookie.net/gensin-impact/images/4/48/Chongyun_Wish.png/revision/latest?cb=20231214214618",
    "Citlali": "https://static.wikia.nocookie.net/gensin-impact/images/a/a4/Citlali_Wish.png/revision/latest?cb=20250101131214",
    "Clorinde": "https://static.wikia.nocookie.net/gensin-impact/images/f/f5/Clorinde_Wish.png/revision/latest?cb=20240605022019",
    "Collei": "https://static.wikia.nocookie.net/gensin-impact/images/6/6b/Collei_Wish.png/revision/latest?cb=20231214214656",
    "Columbina": "https://static.wikia.nocookie.net/gensin-impact/images/2/22/Columbina_Wish.png/revision/latest?cb=20260114052008",
    "Cyno": "https://static.wikia.nocookie.net/gensin-impact/images/1/1a/Cyno_Wish.png/revision/latest?cb=20231214214714",
    "Dahlia": "https://static.wikia.nocookie.net/gensin-impact/images/6/65/Dahlia_Wish.png/revision/latest?cb=20250618025615",
    "Dehya": "https://static.wikia.nocookie.net/gensin-impact/images/0/0f/Dehya_Wish.png/revision/latest?cb=20231214214740",
    "Diluc": "https://static.wikia.nocookie.net/gensin-impact/images/4/4d/Diluc_Wish.png/revision/latest?cb=20231214214809",
    "Diona": "https://static.wikia.nocookie.net/gensin-impact/images/a/a1/Diona_Wish.png/revision/latest?cb=20231214214847",
    "Dori": "https://static.wikia.nocookie.net/gensin-impact/images/0/05/Dori_Wish.png/revision/latest?cb=20231214214907",
    "Durin": "https://static.wikia.nocookie.net/gensin-impact/images/a/a3/Durin_Wish.png/revision/latest?cb=20251204124550",
    "Emilie": "https://static.wikia.nocookie.net/gensin-impact/images/5/5c/Emilie_Wish.png/revision/latest?cb=20240806102508",
    "Escoffier": "https://static.wikia.nocookie.net/gensin-impact/images/8/82/Escoffier_Wish.png/revision/latest?cb=20250507054932",
    "Eula": "https://static.wikia.nocookie.net/gensin-impact/images/4/49/Eula_Wish.png/revision/latest?cb=20240525000630",
    "Faruzan": "https://static.wikia.nocookie.net/gensin-impact/images/3/3a/Faruzan_Wish.png/revision/latest?cb=20231214214958",
    "Fischl": "https://static.wikia.nocookie.net/gensin-impact/images/6/6e/Fischl_Wish.png/revision/latest?cb=20231214215020",
    "Flins": "https://static.wikia.nocookie.net/gensin-impact/images/4/4d/Flins_Wish.png/revision/latest?cb=20250930200926",
    "Freminet": "https://static.wikia.nocookie.net/gensin-impact/images/1/1b/Freminet_Wish.png/revision/latest?cb=20231214215154",
    "Furina": "https://static.wikia.nocookie.net/gensin-impact/images/5/51/Furina_Wish.png/revision/latest?cb=20231108031329",
    "Gaming": "https://static.wikia.nocookie.net/gensin-impact/images/9/98/Gaming_Wish.png/revision/latest?cb=20240131025251",
    "Ganyu": "https://static.wikia.nocookie.net/gensin-impact/images/f/f5/Ganyu_Wish.png/revision/latest?cb=20231214215252",
    "Gorou": "https://static.wikia.nocookie.net/gensin-impact/images/2/25/Gorou_Wish.png/revision/latest?cb=20231214215314",
    "Hu Tao": "https://static.wikia.nocookie.net/gensin-impact/images/b/b2/Hu_Tao_Wish.png/revision/latest?cb=20231214215404",
    "Iansan": "https://static.wikia.nocookie.net/gensin-impact/images/3/3f/Iansan_Wish.png/revision/latest?cb=20250326020044",
    "Ifa": "https://static.wikia.nocookie.net/gensin-impact/images/d/dd/Ifa_Wish.png/revision/latest?cb=20250507054936",
    "Illuga": "https://static.wikia.nocookie.net/gensin-impact/images/0/0f/Illuga_Wish.png/revision/latest?cb=20260205110314",
    "Ineffa": "https://static.wikia.nocookie.net/gensin-impact/images/6/6d/Ineffa_Wish.png/revision/latest?cb=20250730090625",
    "Jahoda": "https://static.wikia.nocookie.net/gensin-impact/images/3/36/Jahoda_Wish.png/revision/latest?cb=20260127111107",
    "Jean": "https://static.wikia.nocookie.net/gensin-impact/images/e/e7/Jean_Wish.png/revision/latest?cb=20231215201156",
    "Kachina": "https://static.wikia.nocookie.net/gensin-impact/images/5/5c/Kachina_Wish.png/revision/latest?cb=20240828061621",
    "Kaedehara Kazuha": "https://static.wikia.nocookie.net/gensin-impact/images/1/1e/Kaedehara_Kazuha_Wish.png/revision/latest?cb=20231214215446",
    "Kaeya": "https://static.wikia.nocookie.net/gensin-impact/images/f/f4/Kaeya_Wish.png/revision/latest?cb=20231214215507",
    "Kamisato Ayaka": "https://static.wikia.nocookie.net/gensin-impact/images/a/a0/Kamisato_Ayaka_Wish.png/revision/latest?cb=20231214215531",
    "Kamisato Ayato": "https://static.wikia.nocookie.net/gensin-impact/images/c/cf/Kamisato_Ayato_Wish.png/revision/latest?cb=20231214215554",
    "Kaveh": "https://static.wikia.nocookie.net/gensin-impact/images/3/39/Kaveh_Wish.png/revision/latest?cb=20231214215626",
    "Keqing": "https://static.wikia.nocookie.net/gensin-impact/images/a/ac/Keqing_Wish.png/revision/latest?cb=20231214215649",
    "Kinich": "https://static.wikia.nocookie.net/gensin-impact/images/5/59/Kinich_Wish.png/revision/latest?cb=20240917124526",
    "Kirara": "https://static.wikia.nocookie.net/gensin-impact/images/5/5e/Kirara_Wish.png/revision/latest?cb=20231214215723",
    "Klee": "https://static.wikia.nocookie.net/gensin-impact/images/f/f4/Klee_Wish.png/revision/latest?cb=20231214215745",
    "Kujou Sara": "https://static.wikia.nocookie.net/gensin-impact/images/c/c7/Kujou_Sara_Wish.png/revision/latest?cb=20231214215801",
    "Kuki Shinobu": "https://static.wikia.nocookie.net/gensin-impact/images/b/b8/Kuki_Shinobu_Wish.png/revision/latest?cb=20231214215822",
    "Lan Yan": "https://static.wikia.nocookie.net/gensin-impact/images/c/cb/Lan_Yan_Wish.png/revision/latest?cb=20250124131305",
    "Lauma": "https://static.wikia.nocookie.net/gensin-impact/images/f/f3/Lauma_Wish.png/revision/latest?cb=20250910024839",
    "Layla": "https://static.wikia.nocookie.net/gensin-impact/images/e/ea/Layla_Wish.png/revision/latest?cb=20231214215857",
    "Linnea": "https://static.wikia.nocookie.net/gensin-impact/images/d/da/Linnea_Wish.png/revision/latest?cb=20260408075929",
    "Lisa": "https://static.wikia.nocookie.net/gensin-impact/images/9/9a/Lisa_Wish.png/revision/latest?cb=20231214215912",
    "Lohen": "https://static.wikia.nocookie.net/gensin-impact/images/f/fe/Lohen_Wish.png/revision/latest?cb=20260609140934",
    "Lynette": "https://static.wikia.nocookie.net/gensin-impact/images/e/e0/Lynette_Wish.png/revision/latest?cb=20231214220012",
    "Lyney": "https://static.wikia.nocookie.net/gensin-impact/images/f/f9/Lyney_Wish.png/revision/latest?cb=20231214220030",
    "Mavuika": "https://static.wikia.nocookie.net/gensin-impact/images/1/17/Mavuika_Wish.png/revision/latest?cb=20250101130321",
    "Mika": "https://static.wikia.nocookie.net/gensin-impact/images/4/43/Mika_Wish.png/revision/latest?cb=20231214220102",
    "Mona": "https://static.wikia.nocookie.net/gensin-impact/images/d/db/Mona_Wish.png/revision/latest?cb=20201119223928",
    "Mualani": "https://static.wikia.nocookie.net/gensin-impact/images/1/14/Mualani_Wish.png/revision/latest?cb=20240828061028",
    "Nahida": "https://static.wikia.nocookie.net/gensin-impact/images/0/05/Nahida_Wish.png/revision/latest?cb=20241010120048",
    "Navia": "https://static.wikia.nocookie.net/gensin-impact/images/8/87/Navia_Wish.png/revision/latest?cb=20231220022233",
    "Nefer": "https://static.wikia.nocookie.net/gensin-impact/images/9/9b/Nefer_Wish.png/revision/latest?cb=20251022051901",
    "Neuvillette": "https://static.wikia.nocookie.net/gensin-impact/images/3/38/Neuvillette_Wish.png/revision/latest?cb=20230927122228",
    "Nicole": "https://static.wikia.nocookie.net/gensin-impact/images/6/6c/Nicole_Wish.png/revision/latest?cb=20260520063741",
    "Nilou": "https://static.wikia.nocookie.net/gensin-impact/images/8/8e/Nilou_Wish.png/revision/latest?cb=20231214220309",
    "Ningguang": "https://static.wikia.nocookie.net/gensin-impact/images/9/90/Ningguang_Wish.png/revision/latest?cb=20231214220333",
    "Noelle": "https://static.wikia.nocookie.net/gensin-impact/images/9/90/Noelle_Wish.png/revision/latest?cb=20231214220409",
    "Ororon": "https://static.wikia.nocookie.net/gensin-impact/images/4/41/Ororon_Wish.png/revision/latest?cb=20241120132727",
    "Prune": "https://static.wikia.nocookie.net/gensin-impact/images/a/ae/Prune_Wish.png/revision/latest?cb=20260520080122",
    "Qiqi": "https://static.wikia.nocookie.net/gensin-impact/images/b/bb/Qiqi_Wish.png/revision/latest?cb=20231214220429",
    "Raiden Shogun": "https://static.wikia.nocookie.net/gensin-impact/images/a/a0/Raiden_Shogun_Wish.png/revision/latest?cb=20241010115901",
    "Razor": "https://static.wikia.nocookie.net/gensin-impact/images/c/c4/Razor_Wish.png/revision/latest?cb=20231214220515",
    "Rosaria": "https://static.wikia.nocookie.net/gensin-impact/images/7/71/Rosaria_Wish.png/revision/latest?cb=20210406175639",
    "Sandrone": "https://static.wikia.nocookie.net/gensin-impact/images/4/41/Sandrone_Wish.png/revision/latest?cb=20260701022155",
    "Sangonomiya Kokomi": "https://static.wikia.nocookie.net/gensin-impact/images/1/18/Sangonomiya_Kokomi_Wish.png/revision/latest?cb=20231214220601",
    "Sayu": "https://static.wikia.nocookie.net/gensin-impact/images/d/da/Sayu_Wish.png/revision/latest?cb=20231214220617",
    "Sethos": "https://static.wikia.nocookie.net/gensin-impact/images/2/2b/Sethos_Wish.png/revision/latest?cb=20240605022507",
    "Shenhe": "https://static.wikia.nocookie.net/gensin-impact/images/8/89/Shenhe_Wish.png/revision/latest?cb=20231214220640",
    "Shikanoin Heizou": "https://static.wikia.nocookie.net/gensin-impact/images/0/09/Shikanoin_Heizou_Wish.png/revision/latest?cb=20231214220707",
    "Sigewinne": "https://static.wikia.nocookie.net/gensin-impact/images/2/25/Sigewinne_Wish.png/revision/latest?cb=20240625102001",
    "Skirk": "https://static.wikia.nocookie.net/gensin-impact/images/e/e8/Skirk_Wish.png/revision/latest?cb=20250618025236",
    "Sucrose": "https://static.wikia.nocookie.net/gensin-impact/images/6/68/Sucrose_Wish.png/revision/latest?cb=20231214220727",
    "Tartaglia": "https://static.wikia.nocookie.net/gensin-impact/images/9/91/Tartaglia_Wish.png/revision/latest?cb=20231214220746",
    "Thoma": "https://static.wikia.nocookie.net/gensin-impact/images/a/a7/Thoma_Wish.png/revision/latest?cb=20231214220847",
    "Tighnari": "https://static.wikia.nocookie.net/gensin-impact/images/5/5e/Tighnari_Wish.png/revision/latest?cb=20231214220907",
    "Varesa": "https://static.wikia.nocookie.net/gensin-impact/images/9/93/Varesa_Wish.png/revision/latest?cb=20250326015546",
    "Varka": "https://static.wikia.nocookie.net/gensin-impact/images/8/85/Varka_Wish.png/revision/latest?cb=20260225074015",
    "Venti": "https://static.wikia.nocookie.net/gensin-impact/images/f/ff/Venti_Wish.png/revision/latest?cb=20231214220929",
    "Wanderer": "https://static.wikia.nocookie.net/gensin-impact/images/d/d7/Wanderer_Wish.png/revision/latest?cb=20231214220945",
    "Wriothesley": "https://static.wikia.nocookie.net/gensin-impact/images/e/e2/Wriothesley_Wish.png/revision/latest?cb=20231220022622",
    "Xiangling": "https://static.wikia.nocookie.net/gensin-impact/images/b/be/Xiangling_Wish.png/revision/latest?cb=20231214221004",
    "Xianyun": "https://static.wikia.nocookie.net/gensin-impact/images/0/0c/Xianyun_Wish.png/revision/latest?cb=20240131024715",
    "Xiao": "https://static.wikia.nocookie.net/gensin-impact/images/4/46/Xiao_Wish.png/revision/latest?cb=20231214221022",
    "Xilonen": "https://static.wikia.nocookie.net/gensin-impact/images/0/08/Xilonen_Wish.png/revision/latest?cb=20241009114824",
    "Xingqiu": "https://static.wikia.nocookie.net/gensin-impact/images/8/89/Xingqiu_Wish.png/revision/latest?cb=20231214221051",
    "Xinyan": "https://static.wikia.nocookie.net/gensin-impact/images/0/03/Xinyan_Wish.png/revision/latest?cb=20231214221112",
    "Yae Miko": "https://static.wikia.nocookie.net/gensin-impact/images/2/27/Yae_Miko_Wish.png/revision/latest?cb=20231214212731",
    "Yanfei": "https://static.wikia.nocookie.net/gensin-impact/images/3/38/Yanfei_Wish.png/revision/latest?cb=20231214221149",
    "Yaoyao": "https://static.wikia.nocookie.net/gensin-impact/images/7/76/Yaoyao_Wish.png/revision/latest?cb=20231214221201",
    "Yelan": "https://static.wikia.nocookie.net/gensin-impact/images/d/d8/Yelan_Wish.png/revision/latest?cb=20231214221239",
    "Yoimiya": "https://static.wikia.nocookie.net/gensin-impact/images/3/34/Yoimiya_Wish.png/revision/latest?cb=20231214221255",
    "Yumemizuki Mizuki": "https://static.wikia.nocookie.net/gensin-impact/images/3/32/Yumemizuki_Mizuki_Wish.png/revision/latest?cb=20250212083556",
    "Yun Jin": "https://static.wikia.nocookie.net/gensin-impact/images/4/48/Yun_Jin_Wish.png/revision/latest?cb=20231214221307",
    "Zhongli": "https://static.wikia.nocookie.net/gensin-impact/images/2/20/Zhongli_Wish.png/revision/latest?cb=20231214212714",
    "Zibai": "https://static.wikia.nocookie.net/gensin-impact/images/0/0b/Zibai_Wish.png/revision/latest?cb=20260205111420"
}

HSR_CHARACTERS = {
    "Acheron": "https://static.wikia.nocookie.net/houkai-star-rail/images/7/78/Character_Acheron_Splash_Art.png/revision/latest?cb=20240327021325",
    "Aglaea": "https://static.wikia.nocookie.net/houkai-star-rail/images/8/81/Character_Aglaea_Splash_Art.png/revision/latest?cb=20250117063425",
    "Anaxa": "https://static.wikia.nocookie.net/houkai-star-rail/images/7/73/Character_Anaxa_Splash_Art.png/revision/latest?cb=20250409035048",
    "Archer": "https://static.wikia.nocookie.net/houkai-star-rail/images/2/25/Character_Archer_Splash_Art.png/revision/latest?cb=20250620172923",
    "Argenti": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/90/Character_Argenti_Splash_Art.png/revision/latest?cb=20231206232011",
    "Arlan": "https://static.wikia.nocookie.net/houkai-star-rail/images/5/5b/Character_Arlan_Splash_Art.png/revision/latest?cb=20230216231038",
    "Ashveil": "https://static.wikia.nocookie.net/houkai-star-rail/images/d/d4/Character_Ashveil_Splash_Art.png/revision/latest?cb=20260313174406",
    "Asta": "https://static.wikia.nocookie.net/houkai-star-rail/images/b/bd/Character_Asta_Splash_Art.png/revision/latest?cb=20230216231122",
    "Aventurine": "https://static.wikia.nocookie.net/houkai-star-rail/images/a/a9/Character_Aventurine_Splash_Art.png/revision/latest?cb=20240327104723",
    "Bailu": "https://static.wikia.nocookie.net/houkai-star-rail/images/e/e9/Character_Bailu_Splash_Art.png/revision/latest?cb=20230210120736",
    "Black Swan": "https://static.wikia.nocookie.net/houkai-star-rail/images/f/fd/Character_Black_Swan_Splash_Art.png/revision/latest?cb=20240220023547",
    "Blade": "https://static.wikia.nocookie.net/houkai-star-rail/images/1/16/Character_Blade_Splash_Art.png/revision/latest?cb=20230501004859",
    "Boothill": "https://static.wikia.nocookie.net/houkai-star-rail/images/b/bb/Character_Boothill_Splash_Art.png/revision/latest?cb=20240624231026",
    "Bronya": "https://static.wikia.nocookie.net/houkai-star-rail/images/7/7c/Character_Bronya_Splash_Art.png/revision/latest?cb=20240121130128",
    "Castorice": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/94/Character_Castorice_Splash_Art.png/revision/latest?cb=20250409035111",
    "Cerydra": "https://static.wikia.nocookie.net/houkai-star-rail/images/b/ba/Character_Cerydra_Splash_Art.png/revision/latest?cb=20250725220412",
    "Cipher": "https://static.wikia.nocookie.net/houkai-star-rail/images/0/0d/Character_Cipher_Splash_Art.png/revision/latest?cb=20250725220236",
    "Clara": "https://static.wikia.nocookie.net/houkai-star-rail/images/c/c2/Character_Clara_Splash_Art.png/revision/latest?cb=20230216231958",
    "Cyrene": "https://static.wikia.nocookie.net/houkai-star-rail/images/8/8b/Character_Cyrene_Splash_Art.png/revision/latest?cb=20251105032126",
    "Dan Heng": "https://static.wikia.nocookie.net/houkai-star-rail/images/e/e5/Character_Dan_Heng_Splash_Art.png/revision/latest?cb=20230525090149",
    "Evanescia": "https://static.wikia.nocookie.net/houkai-star-rail/images/2/2f/Character_Evanescia_Splash_Art.png/revision/latest?cb=20260506070712",
    "Feixiao": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/61/Character_Feixiao_Splash_Art.png/revision/latest?cb=20241007220552",
    "Firefly": "https://static.wikia.nocookie.net/houkai-star-rail/images/3/38/Character_Firefly_Splash_Art.png/revision/latest?cb=20241007220547",
    "Fu Xuan": "https://static.wikia.nocookie.net/houkai-star-rail/images/3/3e/Character_Fu_Xuan_Splash_Art.png/revision/latest?cb=20230928224921",
    "Gallagher": "https://static.wikia.nocookie.net/houkai-star-rail/images/2/2d/Character_Gallagher_Splash_Art.png/revision/latest?cb=20240327022011",
    "Gepard": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/96/Character_Gepard_Splash_Art.png/revision/latest?cb=20230216232354",
    "Gilgamesh": "https://static.wikia.nocookie.net/houkai-star-rail/images/4/4f/Character_Gilgamesh_Splash_Art.png/revision/latest?cb=20260724102153",
    "Guinaifen": "https://static.wikia.nocookie.net/houkai-star-rail/images/3/33/Character_Guinaifen_Splash_Art.png/revision/latest?cb=20231030040741",
    "Hanya": "https://static.wikia.nocookie.net/houkai-star-rail/images/e/e8/Character_Hanya_Splash_Art.png/revision/latest?cb=20231206232120",
    "Herta": "https://static.wikia.nocookie.net/houkai-star-rail/images/8/8c/Character_Herta_Splash_Art.png/revision/latest?cb=20230216231220",
    "Himeko": "https://static.wikia.nocookie.net/houkai-star-rail/images/8/8e/Character_Himeko_Splash_Art.png/revision/latest?cb=20230525090036",
    "Hook": "https://static.wikia.nocookie.net/houkai-star-rail/images/e/ec/Character_Hook_Splash_Art.png/revision/latest?cb=20230525090126",
    "Huohuo": "https://static.wikia.nocookie.net/houkai-star-rail/images/8/82/Character_Huohuo_Splash_Art.png/revision/latest?cb=20250604025217",
    "Hyacine": "https://static.wikia.nocookie.net/houkai-star-rail/images/7/7d/Character_Hyacine_Splash_Art.png/revision/latest?cb=20250521031729",
    "Hysilens": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/60/Character_Hysilens_Splash_Art.png/revision/latest?cb=20250720121134",
    "Jade": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/6d/Character_Jade_Splash_Art.png/revision/latest?cb=20240706170539",
    "Jiaoqiu": "https://static.wikia.nocookie.net/houkai-star-rail/images/b/be/Character_Jiaoqiu_Splash_Art.png/revision/latest?cb=20240911023034",
    "Jing Yuan": "https://static.wikia.nocookie.net/houkai-star-rail/images/4/48/Character_Jing_Yuan_Splash_Art.png/revision/latest?cb=20230210115809",
    "Jingliu": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/97/Character_Jingliu_Splash_Art.png/revision/latest?cb=20240525000314",
    "Kafka": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/95/Character_Kafka_Splash_Art.png/revision/latest?cb=20230809042240",
    "Lingsha": "https://static.wikia.nocookie.net/houkai-star-rail/images/c/c1/Character_Lingsha_Splash_Art.png/revision/latest?cb=20241120224130",
    "Luka": "https://static.wikia.nocookie.net/houkai-star-rail/images/5/51/Character_Luka_Splash_Art.png/revision/latest?cb=20230809042157",
    "Luocha": "https://static.wikia.nocookie.net/houkai-star-rail/images/a/a5/Character_Luocha_Splash_Art.png/revision/latest?cb=20230628091054",
    "Lynx": "https://static.wikia.nocookie.net/houkai-star-rail/images/3/3c/Character_Lynx_Splash_Art.png/revision/latest?cb=20230719101506",
    "March 7th": "https://static.wikia.nocookie.net/houkai-star-rail/images/c/c7/Character_March_7th_%28Preservation%29_Splash_Art.png/revision/latest?cb=20230525090156",
    "Misha": "https://static.wikia.nocookie.net/houkai-star-rail/images/5/5c/Character_Misha_Splash_Art.png/revision/latest?cb=20240206022717",
    "Mortenax Blade": "https://static.wikia.nocookie.net/houkai-star-rail/images/4/4b/Character_Mortenax_Blade_Splash_Art.png/revision/latest?cb=20260601025859",
    "Moze": "https://static.wikia.nocookie.net/houkai-star-rail/images/8/81/Character_Moze_Splash_Art.png/revision/latest?cb=20240910181952",
    "Mydei": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/67/Character_Mydei_Splash_Art.png/revision/latest?cb=20250725220512",
    "Natasha": "https://static.wikia.nocookie.net/houkai-star-rail/images/7/7e/Character_Natasha_Splash_Art.png/revision/latest?cb=20240525042421",
    "Pela": "https://static.wikia.nocookie.net/houkai-star-rail/images/c/c9/Character_Pela_Splash_Art.png/revision/latest?cb=20230525090100",
    "Phainon": "https://static.wikia.nocookie.net/houkai-star-rail/images/4/47/Character_Phainon_Splash_Art.png/revision/latest?cb=20250622125151",
    "Qingque": "https://static.wikia.nocookie.net/houkai-star-rail/images/d/d1/Character_Qingque_Splash_Art.png/revision/latest?cb=20230210115335",
    "Fugue": "https://static.wikia.nocookie.net/houkai-star-rail/images/4/4c/Character_Fugue_Splash_Art.png/revision/latest?cb=20241122125941",
    "Rappa": "https://static.wikia.nocookie.net/houkai-star-rail/images/1/1c/Character_Rappa_Splash_Art.png/revision/latest?cb=20241120154734",
    "Rin Tohsaka": "https://static.wikia.nocookie.net/houkai-star-rail/images/0/04/Character_Rin_Tohsaka_Splash_Art.png/revision/latest?cb=20260724102152",
    "Robin": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/92/Character_Robin_Splash_Art.png/revision/latest?cb=20240508021256",
    "Ruan Mei": "https://static.wikia.nocookie.net/houkai-star-rail/images/d/d5/Character_Ruan_Mei_Splash_Art.png/revision/latest?cb=20231227021137",
    "Saber": "https://static.wikia.nocookie.net/houkai-star-rail/images/0/04/Character_Saber_Splash_Art.png/revision/latest?cb=20250620172940",
    "Sampo": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/65/Character_Sampo_Splash_Art.png/revision/latest?cb=20230525090046",
    "Seele": "https://static.wikia.nocookie.net/houkai-star-rail/images/5/58/Character_Seele_Splash_Art.png/revision/latest?cb=20240121123334",
    "Serval": "https://static.wikia.nocookie.net/houkai-star-rail/images/8/8a/Character_Serval_Splash_Art.png/revision/latest?cb=20230525090108",
    "Silver Wolf": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/60/Character_Silver_Wolf_Splash_Art.png/revision/latest?cb=20230216230911",
    "Sparkle": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/99/Character_Sparkle_Splash_Art.png/revision/latest?cb=20240327022635",
    "Sparxie": "https://static.wikia.nocookie.net/houkai-star-rail/images/a/ab/Character_Sparxie_Splash_Art.png/revision/latest?cb=20260206131556",
    "Sunday": "https://static.wikia.nocookie.net/houkai-star-rail/images/2/21/Character_Sunday_Splash_Art.png/revision/latest?cb=20241224161538",
    "Sushang": "https://static.wikia.nocookie.net/houkai-star-rail/images/7/72/Character_Sushang_Splash_Art.png/revision/latest?cb=20230210115023",
    "The Dahlia": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/92/Character_The_Dahlia_Splash_Art.png/revision/latest?cb=20251205121609",
    "The Herta": "https://static.wikia.nocookie.net/houkai-star-rail/images/4/42/Character_The_Herta_Splash_Art.png/revision/latest?cb=20250121214107",
    "Tingyun": "https://static.wikia.nocookie.net/houkai-star-rail/images/5/5b/Character_Tingyun_Splash_Art.png/revision/latest?cb=20230210115502",
    "Topaz & Numby": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/9d/Character_Topaz_and_Numby_Splash_Art.png/revision/latest?cb=20231030040101",
    "Tribbie": "https://static.wikia.nocookie.net/houkai-star-rail/images/e/eb/Character_Tribbie_Splash_Art.png/revision/latest?cb=20250309185506",
    "Welt": "https://static.wikia.nocookie.net/houkai-star-rail/images/1/11/Character_Welt_Splash_Art.png/revision/latest?cb=20230525090017",
    "Xueyi": "https://static.wikia.nocookie.net/houkai-star-rail/images/b/bc/Character_Xueyi_Splash_Art.png/revision/latest?cb=20231227045314",
    "Yanqing": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/6d/Character_Yanqing_Splash_Art.png/revision/latest?cb=20230210121516",
    "Yao Guang": "https://static.wikia.nocookie.net/houkai-star-rail/images/e/e1/Character_Yao_Guang_Splash_Art.png/revision/latest?cb=20260213053032",
    "Yukong": "https://static.wikia.nocookie.net/houkai-star-rail/images/0/04/Character_Yukong_Splash_Art.png/revision/latest?cb=20230628090836",
    "Yunli": "https://static.wikia.nocookie.net/houkai-star-rail/images/7/72/Character_Yunli_Splash_Art.png/revision/latest?cb=20241007221656"
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
        anilist_id = 9910000 + abs(hash(name)) % 100000
        rarity = "🔷 Rare" if name in LOW_RARITY_HINTS else "✨ Legendary"
        favs = 3000 if rarity == "🔷 Rare" else 12000

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

    # 2. Honkai: Star Rail Characters (92 total)
    print(f"🎮 Seeding {len(HSR_CHAR_NAMES)} Honkai: Star Rail characters...")
    for name in HSR_CHAR_NAMES:
        img_url = HSR_CHARACTERS.get(name)
        if not img_url:
            c_clean = name.replace(' • ', '_').replace(' & ', '_and_').replace('.', '').replace(':', '').replace(' ', '_')
            img_url = f"https://static.wikia.nocookie.net/houkai-star-rail/images/8/80/Character_{c_clean}_Splash_Art.png"

        anilist_id = 9920000 + abs(hash(name)) % 100000
        rarity = "🔷 Rare" if name in LOW_RARITY_HINTS or name in ['March 7th', 'Welt', 'Himeko', 'Arlan', 'Asta', 'Hook', 'Natasha', 'Misha', 'Sushang', 'Yukong'] else "✨ Legendary"
        favs = 3000 if rarity == "🔷 Rare" else 12000

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
