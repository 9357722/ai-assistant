import urllib.request, os, hashlib, time

folder = 'D:/python/AI_Projects/static/products'
os.makedirs(folder, exist_ok=True)

products = [
    'iPhone_15_Pro_Max', 'iPhone_15_Pro', 'iPhone_15', 'iPhone_14', 'iPhone_13',
    'Huawei_Mate60_Pro', 'Huawei_Mate60', 'Huawei_P60_Pro', 'Huawei_Nova12', 'Huawei_Pura70',
    'Xiaomi_14_Pro', 'Xiaomi_14', 'Xiaomi_13', 'Xiaomi_Civi4', 'Xiaomi_Turbo3',
    'Redmi_K70_Pro', 'Redmi_K70', 'Redmi_Note13', 'Redmi_Turbo3', 'Redmi_A3',
    'OPPO_Find_X7', 'OPPO_Reno11', 'OPPO_A3', 'OPPO_K12', 'OPPO_A2',
    'vivo_X100_Pro', 'vivo_X100', 'vivo_Y100', 'vivo_Y78', 'vivo_S19',
    'OnePlus_12', 'OnePlus_Ace3', 'OnePlus_Nord', 'OnePlus_11', 'OnePlus_Ace2',
    'Samsung_S24_Ultra', 'Samsung_S24', 'Samsung_S23', 'Samsung_A55', 'Samsung_A35',
    'Honor_Magic6', 'Honor_X50', 'Honor_200', 'Honor_X60', 'Honor_Play8',
    'iQOO_12', 'iQOO_Neo9', 'iQOO_Z9', 'Meizu_21', 'Nothing_Phone',
    'MacBook_Pro_14', 'MacBook_Pro_16', 'MacBook_Air_13', 'MacBook_Air_15', 'Mac_Mini',
    'ThinkPad_X1', 'ThinkPad_T14', 'ThinkPad_E16', 'ThinkPad_L14', 'ThinkPad_S2',
    'Huawei_MateBook_X', 'Huawei_MateBook_D16', 'Huawei_MateBook_14', 'Huawei_MateBook_S', 'Huawei_MateBook_B',
    'Xiaoxin_Pro16', 'Xiaoxin_14', 'Xiaoxin_Air14', 'Xiaoxin_Plus16', 'Xiaoxin_16',
    'ASUS_ROG_Strix', 'ASUS_TUF_Gaming', 'ASUS_VivoBook', 'ASUS_ZenBook', 'ASUS_ProArt',
    'HP_Omen_16', 'HP_Spectre', 'HP_Envy', 'HP_Pavilion', 'HP_ProBook',
    'Dell_XPS_15', 'Dell_Inspiron', 'Dell_Latitude', 'Dell_G16', 'Dell_Vostro',
    'RedmiBook_16', 'RedmiBook_14', 'RedmiBook_Pro', 'RedmiBook_Air', 'RedmiBook_E',
    'Lenovo_Y9000P', 'Lenovo_Y7000P', 'Lenovo_Legion', 'Lenovo_IdeaPad', 'Lenovo_Approach',
    'MSI_Titan', 'MSI_RAIDER', 'MSI_PRESTIGE', 'MSI_VECTOR', 'MSI_STEALTH',
    'iPad_Pro_13', 'iPad_Pro_11', 'iPad_Air_11', 'iPad_Air_13', 'iPad_10', 'iPad_Mini', 'iPad_9', 'iPad_8', 'iPad_Pro_12', 'iPad_Air_M2',
    'Huawei_MatePad_Pro_13', 'Huawei_MatePad_11', 'Huawei_MatePad_SE', 'Huawei_MatePad_Air', 'Huawei_MatePad_T',
    'Xiaomi_Pad_6_Pro', 'Xiaomi_Pad_6', 'Xiaomi_Pad_5', 'Xiaomi_Pad_SE', 'Xiaomi_Pad_6S_Pro',
    'Samsung_Tab_S9_Ultra', 'Samsung_Tab_S9', 'Samsung_Tab_A9', 'Samsung_Tab_S8', 'Samsung_Tab_FE',
    'Lenovo_Yoga_Pad', 'Lenovo_XiaoXin_Pad', 'Lenovo_P12', 'Lenovo_Tab_P11', 'Lenovo_Tab_E',
    'OPPO_Pad_2', 'OPPO_Pad_Air', 'vivo_Pad3', 'vivo_Pad2', 'vivo_Pad_Air',
    'Microsoft_Surface_Pro', 'Microsoft_Surface_Go', 'Microsoft_Surface_9', 'Microsoft_Surface_Laptop', 'Microsoft_Surface_Duo',
    'Honor_Pad_9', 'Honor_Pad_V8', 'Honor_Pad_X8', 'Honor_Pad_8', 'Honor_Pad_Z7',
    'Realme_Pad_2', 'Redmi_Pad_Pro', 'iQOO_Pad2', 'OnePlus_Pad', 'Nothing_Pad',
    'AirPods_Pro_2', 'AirPods_3', 'AirPods_Max', 'AirPods_2', 'Beats_Fit_Pro',
    'Huawei_FreeBuds_Pro_3', 'Huawei_FreeBuds_5', 'Huawei_FreeBuds_SE2', 'Huawei_FreeBuds_4i', 'Huawei_FreeBuds_E',
    'Sony_WH_1000XM5', 'Sony_WF_1000XM5', 'Sony_WH_1000XM4', 'Sony_WF_SP800N', 'Sony_LinkBuds',
    'Xiaomi_Buds_4_Pro', 'Xiaomi_Buds_4', 'Xiaomi_Buds_3', 'Xiaomi_Buds_5', 'Xiaomi_Headphones',
    'Edifier_W820NB', 'Edifier_Stax_Spirit', 'Edifier_Neobuds', 'Edifier_W830NB', 'Edifier_Hecate',
    'Samsung_Galaxy_Buds3', 'Samsung_Galaxy_Buds2', 'Samsung_Galaxy_Buds_Fe', 'Samsung_Galaxy_Buds_Live', 'Samsung_Galaxy_Buds_Pro',
    'JBL_Tour_M2', 'JBL_Vibe', 'JBL_Live', 'JBL_Tune', 'JBL_Quantum',
    'Bose_QC_Ultra', 'Bose_700', 'Bose_QC45', 'Bose_Sport', 'Bose_Comfort',
    'Sennheiser_Momentum', 'Sennheiser_CX', 'Sennheiser_IE', 'Sennheiser_HD', 'Sennheiser_Evo',
    'Shokz_OpenRun', 'Shokz_OpenFit', 'Shokz_OpenComm', 'Shokz_AS660', 'Shokz_AS800',
    'Apple_Watch_Ultra_2', 'Apple_Watch_S9', 'Apple_Watch_SE', 'Apple_Watch_Ultra', 'Apple_Watch_S8',
    'Huawei_Watch_GT4', 'Huawei_Watch_4_Pro', 'Huawei_Watch_3', 'Huawei_Watch_Fit3', 'Huawei_Watch_D2',
    'Xiaomi_Watch_S3', 'Xiaomi_Watch_2_Pro', 'Xiaomi_Watch_S1', 'Xiaomi_Band_8_Pro', 'Xiaomi_Band_8',
    'Samsung_Galaxy_Watch6', 'Samsung_Galaxy_Watch_Fe', 'Samsung_Galaxy_Watch5', 'Samsung_Galaxy_Watch4', 'Samsung_Galaxy_Buds_Watch',
    'Garmin_Fenix_7', 'Garmin_Venu_3', 'Garmin_Forerunner_265', 'Garmin_Enduro_2', 'Garmin_Impulse',
    'OPPO_Watch_4_Pro', 'OPPO_Watch_3', 'OPPO_Watch_2', 'OPPO_Watch_SE', 'OPPO_Band',
    'vivo_Watch_3', 'vivo_Watch_2', 'vivo_Band', 'Amazfit_GTR_4', 'Amazfit_Bip',
    'Honor_Watch_4', 'Honor_Watch_GS3', 'Honor_Watch_ES2', 'TicWatch_Pro_5', 'TicWatch_GTX',
    'Casio_G_Shot', 'Suunto_Peak', 'COROS_Pace3', 'Zepp_Z', 'OnePlus_Watch_2',
    'Sony_A7M4', 'Sony_A7C_II', 'Sony_A7R_V', 'Sony_A1', 'Sony_A9_III',
    'Canon_R6_Mark_II', 'Canon_R5', 'Canon_R8', 'Canon_R7', 'Canon_R10',
    'Nikon_Z8', 'Nikon_Z9', 'Nikon_Z6_III', 'Nikon_Z5', 'Nikon_Zfc',
    'Fujifilm_X_T5', 'Fujifilm_X_S20', 'Fujifilm_X_H2S', 'Fujifilm_X100VI', 'Fujifilm_GFX100',
    'Leica_Q3', 'Leica_M11', 'Leica_SL3', 'Leica_Sofort', 'Leica_D_Lux',
    'DJI_Mavic_4', 'DJI_Osmo_Pocket_3', 'DJI_Action_4', 'DJI_Air_3', 'DJI_Mini_4',
    'GoPro_Hero_12', 'GoPro_Hero_11', 'GoPro_Max', 'GoPro_Fusion', 'GoPro_Session',
    'Insta360_X4', 'Insta360_X3', 'Insta360_GO_3', 'Insta360_One_RS', 'Insta360_Pro2',
    'Hasselblad_X2D', 'Phase_One_IQ4', 'Pentax_K3_III', 'Olympus_EM1', 'Sigma_FP',
    'Zeiss_Consus', 'Tamron_28_75', 'Sigma_35_Art', 'Tokina_Series', 'Samyang_Lens',
    'Dyson_V15', 'Dyson_Airwrap', 'Dyson_Purifier', 'Dyson_Hot_Cool', 'Dyson_AM09',
    'Midea_Cooker', 'Midea_AC', 'Midea_Washer', 'Midea_Fridge', 'Midea_Water_Heater',
    'Gree_AC', 'Gree_Fan', 'Gree_Dehumidifier', 'Gree_Heater', 'Gree_Purifier',
    'Haier_Washer', 'Haier_Fridge', 'Haier_AC', 'Haier_Dryer', 'Haier_Dishwasher',
    'Xiaomi_Air_Purifier', 'Xiaomi_Scooter', 'Xiaomi_Camera', 'Xiaomi_Plug', 'Xiaomi_Lamp',
    'Roborock_S8', 'Ecovacs_X2', 'iRobot_J7', 'Dreame_L10s', 'Narwal_Freo',
    'Samsung_Bespoke', 'LG_WashTower', 'Bosch_Washer', 'Siemens_Dryer', 'Miele_Vacuum',
    'Panasonic_Nanoe', 'Toshiba_AC', 'Sharp_Plasmacluster', 'Hitachi_Washer', 'Sanyo_Eco',
    'Deerma_Humidifier', 'Bear_Cooker', 'Supor_Wok', 'Lock_Lock_Box', 'Midea_Rice',
    'Philips_S9000', 'Braun_Series9', 'OralB_IO', 'Panasonic_Shaver', 'Flyco_Shaver',
    'Uniqlo_Pants', 'Uniqlo_Tee', 'Uniqlo_Jacket', 'Uniqlo_Heattech', 'Uniqlo_U_Tee',
    'Nike_Dri_FIT_Tee', 'Nike_AF1', 'Nike_Dunk_Low', 'Nike_Jordan', 'Nike_Tech_Fleece',
    'Adidas_Classic_Hoodie', 'Adidas_Stan_Smith', 'Adidas_Ultraboost', 'Adidas_Tiro', 'Adidas_ZX',
    'Li_Ning_Pants', 'Li_Ning_Jacket', 'Li_Ning_Tee', 'Li_Ning_Shoes', 'Li_Ning_Bag',
    'Anta_Shirt', 'Anta_Pants', 'Anta_Jacket', 'Anta_Shoes', 'Anta_Short',
    'NB_574', 'NB_990', 'NB_327', 'NB_2002R', 'NB_FuelCell',
    'Puma_RS_X', 'Puma_Suede', 'Puma_Tee', 'Puma_Jacket', 'Puma_Pants',
    'Levis_501', 'Levis_505', 'Levis_Denim_Jacket', 'Levis_Tee', 'Levis_Shorts',
    'Zara_Blazer', 'Zara_Dress', 'Zara_Tee', 'Zara_Pants', 'Zara_Jacket',
    'HM_Tee', 'HM_Jeans', 'HM_Shirt', 'HM_Sweater', 'HM_Jacket',
    'Lancome_Lotion', 'Lancome_Absolue', 'Lancome_Genifique', 'Lancome_Teint', 'Lancome_Lash',
    'Estee_Lauder_Serum', 'Estee_Lauder_Cream', 'Estee_Lauder_Foundation', 'Estee_Lauder_Night', 'Estee_Lauder_Lip',
    'SKII_FTE', 'SKII_Serum', 'SKII_Cream', 'SKII_Essence', 'SKII_Lotion',
    'MAC_Lipstick', 'MAC_Foundation', 'MAC_Mascara', 'MAC_Eyeshadow', 'MAC_Concealer',
    'Proya_Serum', 'Proya_Cream', 'Proya_Sunscreen', 'Proya_Essence', 'Proya_Mask',
    'Florasis_Lip', 'Florasis_Powder', 'Florasis_Serum', 'Florasis_Eye', 'Florasis_Base',
    'Perfect_Diary_Lip', 'Perfect_Diary_Eye', 'Perfect_Diary_Foundation', 'Perfect_Diary_Powder', 'Perfect_Diary_Blush',
    'Clinique_Moisture', 'Clinique_Serum', 'Clinique_Cleanser', 'Clinique_Eye', 'Clinique_Makeup',
    'Shiseido_Serum', 'Shiseido_Cream', 'Shiseido_Sunscreen', 'Shiseido_Essence', 'Shiseido_Lotion',
    'Kiehls_Cream', 'Kiehls_Serum', 'Kiehls_Cleanser', 'Kiehls_Toner', 'Kiehls_Mask',
    'Three_Body_Trilogy', 'Alive_Novel', 'Sapiens_Book', 'Python_Book', 'AI_Book',
    'Three_Squirrels_Nuts', 'Liangpin_Snacks', 'Nongfu_Water', 'Saturnbird_Coffee', 'Heytea_Coffee',
    'Keep_Yoga_Mat', 'Mi_Band_8', 'Tesla_Model_Y', 'BYD_Seal', 'Xiaomi_SU7',
    'DJI_Mini_4', 'Switch_2', 'PS5_Pro', 'Xbox_X', 'Steam_Deck',
    'LEGO_Set', 'Hot_Toys_Figure', 'Bandai_Model', 'Funko_Pop', 'Nendoroid',
    'Yeti_Tumbler', 'Stanley_Cup', 'Hydro_Flask', 'Zojirushi_Bottle', 'Thermos_Bottle',
    'Kindle_Paperwhite', 'BOOX_Note', 'Supernote_A5X', 'Remarkable_2', 'Dasung_Ereader',
    'Anker_Charger', 'Belkin_Stand', 'Baseus_Cable', 'Ugreen_Adapter', 'Xiaomi_Power_Bank',
    'Logitech_Mouse', 'Razer_Keyboard', 'Corsair_RAM', 'Samsung_SSD', 'WD_Black',
    'LEGO_Technic', 'Hot_Wheels', 'Barbie_Doll', 'Pokemon_Cards', 'Yu_Gi_Oh'
]

existing = set(os.listdir(folder))
count = 0
for name in products:
    filename = f'{name}.jpg'
    if filename in existing:
        continue
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 10000
    url = f'https://picsum.photos/seed/{seed}/400/400'
    filepath = os.path.join(folder, filename)
    try:
        urllib.request.urlretrieve(url, filepath)
        count += 1
        if count % 50 == 0:
            print(f'Downloaded {count}...')
    except:
        pass
    time.sleep(0.05)

print(f'Done. Total: {len(os.listdir(folder))} files, new: {count}')
