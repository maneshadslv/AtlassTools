import requests
import geopandas as gpd
from gooey import GooeyParser, Gooey

trello_cards_link = "https://api.trello.com/1/cards"
apikey = '2e4a6967dcc93370d2582847d6a45726'
atoken = 'a0f7750db6dce905e830089813cb8f7c4611695c8264ba325b1266cb156e4274'
params_presented = {'key': apikey, 'token': atoken}
board_id = "601c6df669ba790ff0ba440a"
checklists_url = "https://api.trello.com/1/checklists"



'''link_to_card = "https://trello.com/c/lqvASATw/354-testing-checklists"
tenk = r"V:\BR03202_Roma-Santos\Area01\01_LiDAR\03_Tiled_and_classified\To_XXX\01_Sent\210818_0625_GDA94_MGA-55_500m_tiles\Tilelayout_10000_block.json"
area_name = 'Roma_Area01'''


def make_checklist(name, card_id):
    checklist_name = '%s 10k Blocks' % name
    copy_params = params_presented.copy()
    copy_params['idCard'] = card_id
    copy_params['name'] = checklist_name
    response = requests.post(checklists_url, copy_params).json()
    return response['id']


def get_card_id(link_in):
    split_link = link_in.split('/')
    '''card_json = requests.get(link_in, params_presented).text
    print(card_json)'''
    # trello is a butt so we need to go via the proper ID for the card. boo.
    link_to_board = "https://api.trello.com/1/boards/{}/cards".format(board_id)
    cards_list = requests.get(link_to_board, params_presented).json()
    for item in cards_list:
        short_link = item['shortLink']
        if short_link == split_link[4]:
            card_id = item['id']
            return card_id


def tile_to_checklist_entry(tile_name, checklist_id):
    checklist_link = "https://api.trello.com/1/checklists/{}/checkItems".format(checklist_id)
    params_copy = params_presented.copy()
    params_copy['name'] = tile_name
    resp = requests.post(checklist_link, params_copy)


def main_process(card_link, tlay, area):
    tlay_gpd = gpd.GeoDataFrame.from_file(tlay)
    card_id = get_card_id(card_link)
    checklist_id = make_checklist(area, card_id)
    for item in list(tlay_gpd['name']):
        block_name = 'Block %s' % item
        print('Inserting %s...' % block_name)
        tile_to_checklist_entry(block_name, checklist_id)


@Gooey(program_name="Quick Trello Checklist Builder", use_legacy_titles=True, required_cols=2, default_size=(750, 500))
def goo():
    parser = GooeyParser(description='10km Checklist Maker')
    parser.add_argument('link_to_card', metavar='Link to card')
    parser.add_argument('tenk', metavar='Path to 10km json', widget='FileChooser')
    parser.add_argument('area_name', metavar='Area_Name')
    return parser.parse_args()


if __name__ == '__main__':
    input_items = goo()
    main_process(input_items.link_to_card, input_items.tenk, input_items.area_name)
