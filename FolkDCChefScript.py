import requests
from bs4 import BeautifulSoup
import re
import os
from ricecooker.chefs import SushiChef
from ricecooker.classes import nodes, files, licenses
from le_utils.constants.languages import getlang_by_name

KOLIBRI_API_KEY = 'bca1e71945d1456dc450211ebf1df799d63d5b7b'

# Run constants
################################################################################
CHANNEL_ID = "d5c3b3aa38fd46c09b4643cea5d21779"  # Test channel ID
CHANNEL_NAME = "Folk DC Testing Channel"  # Name of Kolibri channel
CHANNEL_SOURCE_ID = "folk-dc-testing-channel"  # Unique ID for content source
CHANNEL_DOMAIN = "folkdc.eu"  # Who is providing the content
CHANNEL_LANGUAGE = "en"  # Language of channel
CHANNEL_DESCRIPTION = "A collection of multi-language folk songs and activities for primary students to learn languages, engage in collaboration and critical thinking, and develop intercultural skills. Contains folk songs, activity suggestions, and teacher training materials."  # Description of the channel (optional)
CHANNEL_THUMBNAIL = "http://folkdc.eu/img/Folk8-200.png"  # Local path or url to image file (optional)
CONTENT_ARCHIVE_VERSION = 1
LICENSE = licenses.AllRightsLicense('Folk DC')

# Additional constants
################################################################################
CREDENTIALS = os.path.join("credentials", "credentials.json")
# AUDIO_FOLDER = os.path.abspath(os.path.join("chefdata", "audios"))
AUDIO_FOLDER = os.path.join("chefdata", "audios")
# PDF_FOLDER = os.path.abspath(os.path.join("chefdata", "pdfbooks"))
PDF_FOLDER = os.path.join("chefdata", "pdfbooks")

STATIC_URL_SONGS = "http://folkdc.eu/resources/folksongs/"
STATIC_URL_ACTIVITIES = "http://folkdc.eu/handbook/"

SESSION = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
}
SESSION.headers = headers


class FolkDcChef(SushiChef):
    channel_info = {
        'CHANNEL_ID': CHANNEL_ID,
        'CHANNEL_SOURCE_DOMAIN': CHANNEL_DOMAIN,
        'CHANNEL_SOURCE_ID': CHANNEL_SOURCE_ID,
        'CHANNEL_TITLE': CHANNEL_NAME,
        'CHANNEL_LANGUAGE': CHANNEL_LANGUAGE,
        'CHANNEL_DESCRIPTION': CHANNEL_DESCRIPTION,
    }
    ASSETS_DIR = os.path.abspath('assets')
    DATA_DIR = os.path.abspath('chefdata')
    DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')
    ARCHIVE_DIR = os.path.join(DOWNLOADS_DIR, 'archive_{}'.format(CONTENT_ARCHIVE_VERSION))

    def download_pdf_from_url(self, pdf_url):
        orig_filename = os.path.basename(pdf_url)
        folder_dir_path = os.path.join(PDF_FOLDER)
        if not os.path.exists(folder_dir_path):
            os.makedirs(folder_dir_path)
        orig_path = os.path.join(folder_dir_path, orig_filename)

        # download original PDF if needed
        if not os.path.exists(orig_path):
            response = SESSION.get(pdf_url)
            with open(orig_path, 'wb') as pdf_file:
                pdf_file.write(response.content)

        return orig_path

    def download_video(self, video_url, file_name):
        r = SESSION.get(video_url, stream=True)
        if not os.path.exists(AUDIO_FOLDER):
            os.makedirs(AUDIO_FOLDER)
        audio_path = f'{AUDIO_FOLDER}/{file_name}'
        with open(audio_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        return audio_path

    def scraping_att_songs_and_templates(self):
        response = SESSION.get(STATIC_URL_SONGS)
        page = BeautifulSoup(response.text, 'html5lib')

        lst_items = page.find_all('tbody')

        lst_scrapped = []
        for table_body in lst_items:
            rows = table_body.find_all('tr')
            for row in rows:
                dict_tmp = {}
                tds = row.find_all('td')
                for td in tds:
                    if td.find('div'):
                        song_name = td.find('div').get_text()
                        song_name = re.sub(r'[^A-Za-z0-9 ]+', '', song_name)
                        dict_tmp['song_name'] = song_name
                    elif td.find('a'):
                        url_link = td.find('a')
                        if url_link['href'].endswith('mp3'):
                            dict_tmp['url_link'] = url_link['href']
                        if url_link['href'].endswith('pdf'):
                            dict_tmp['pdf_link'] = url_link['href']
                    else:
                        text = td.get_text()
                        dict_tmp['language'] = text
                if dict_tmp:
                    lst_scrapped.append(dict_tmp)

            for dict_scrapped in lst_scrapped:
                dict_scrapped['audio_path'] = self.download_video(dict_scrapped.get('url_link'),
                                                                  dict_scrapped.get('song_name'))
                dict_scrapped['pdf_path'] = self.download_pdf_from_url(dict_scrapped.get('pdf_link'))

        return lst_scrapped

    def scrapping_activities(self):
        is_language = False
        is_cultural = False
        is_musical = False

        dict_lst_scrapped = {"Activities": {}}

        response = SESSION.get(STATIC_URL_ACTIVITIES)
        page = BeautifulSoup(response.text, 'html5lib')
        lst_items = page.find_all('p')

        for p_body in lst_items:
            if p_body.get_text() == "LANGUAGE ACTIVITIES":
                is_language = True
            elif p_body.get_text() == "CULTURAL ACTIVITIES":
                is_language = False
                is_musical = False
                is_cultural = True
            elif p_body.get_text() == "MUSICAL ACTIVITIES":
                is_language = False
                is_cultural = False
                is_musical = True
            if "Activity" in p_body.get_text():
                # lst_splitted = p_body.contents
                lst_pdf_links = []
                lst_splitted = p_body.text.split('\n')
                lst_hrefs = p_body.find_all('a')
                for link in lst_hrefs:
                    current_link = link.get('href')
                    if current_link.endswith('pdf'):
                        lst_pdf_links.append(current_link)
                counter = 0
                for index in range(0, len(lst_splitted)):
                    p_text = re.sub(r'[^A-Za-z0-9 ]+', '', str(lst_splitted[index]))
                    if p_text and "\n" not in lst_splitted[index] and "<br" not in lst_splitted[index]:
                        p_text = p_text.strip()
                        pdf_path = self.download_pdf_from_url(lst_pdf_links[counter])
                        dict_tmp = {
                            'pdf_name': p_text,
                            'pdf_path': pdf_path}
                        if is_language:
                            dict_activities = dict_lst_scrapped.get('Activities')
                            if not dict_activities.get('LANGUAGE ACTIVITIES'):
                                dict_lst_scrapped['Activities']['LANGUAGE ACTIVITIES'] = [dict_tmp]
                            else:
                                dict_lst_scrapped['Activities']['LANGUAGE ACTIVITIES'].append(dict_tmp)

                        if is_musical:
                            dict_activities = dict_lst_scrapped.get('Activities')
                            if not dict_activities.get('MUSICAL ACTIVITIES'):
                                dict_lst_scrapped['Activities']['MUSICAL ACTIVITIES'] = [dict_tmp]
                            else:
                                dict_lst_scrapped['Activities']['MUSICAL ACTIVITIES'].append(dict_tmp)
                        if is_cultural:
                            dict_activities = dict_lst_scrapped.get('Activities')
                            if not dict_activities.get('CULTURAL ACTIVITIES'):
                                dict_lst_scrapped['Activities']['CULTURAL ACTIVITIES'] = [dict_tmp]
                            else:
                                dict_lst_scrapped['Activities']['CULTURAL ACTIVITIES'].append(dict_tmp)
                        counter = counter + 1
        return dict_lst_scrapped

    def construct_channel(self, *args, **kwargs):
        """
        Creates ChannelNode and build topic tree
        Args:
          - args: arguments passed in on the command line
          - kwargs: extra options passed in as key="value" pairs on the command line
            For example, add the command line option   lang="fr"  and the value
            "fr" will be passed along to `construct_channel` as kwargs['lang'].
        Returns: ChannelNode
        """
        """
        Channel structure:
            Language > Introduction > Song > Topic Name > Content
        """

        lst_dict_scrapped = self.scraping_att_songs_and_templates()
        dict_activities = self.scrapping_activities()
        channel_info = self.channel_info
        channel = nodes.ChannelNode(
            source_domain=channel_info['CHANNEL_SOURCE_DOMAIN'],
            source_id=channel_info['CHANNEL_SOURCE_ID'],
            title=channel_info['CHANNEL_TITLE'],
            thumbnail=channel_info.get('CHANNEL_THUMBNAIL'),
            description=channel_info.get('CHANNEL_DESCRIPTION'),
            language="en",
        )

        if not os.path.exists(AUDIO_FOLDER):
            os.makedirs(AUDIO_FOLDER, exist_ok=True)

        dict_scrapped_stuffs = {'songs': lst_dict_scrapped}
        dict_scrapped_stuffs.update(dict_activities)
        channel = self.upload_content(dict_scrapped_stuffs, channel)

        return channel

    def upload_content(self, dict_content, channel):
        song_node = nodes.TopicNode(
            title="Songs",
            source_id="Songs",
            description="All songs"
        )
        lst_dict_items = dict_content.get('songs')
        for dict_item in lst_dict_items:
            language_node = nodes.TopicNode(
                title=dict_item.get('song_name'),
                source_id=dict_item.get('song_name'),
                author="FolkDC",
                description="",
                language=getlang_by_name(dict_item.get('language'))
            )

            audio_file = files.AudioFile(path=dict_item.get('audio_path'))
            audio_node = nodes.AudioNode(
                source_id=f'{dict_item.get("song_name")}-Audio',
                title=dict_item.get('song_name'),
                license=LICENSE,
                files=[audio_file]
            )
            pdf_node = nodes.DocumentNode(
                title='Details',
                source_id=f'{dict_item.get("song_name")}-PDF',
                description='Lyrics',
                language=getlang_by_name(dict_item.get('language')),
                license=LICENSE,
                files=[files.DocumentFile(dict_item.get('pdf_path'))]
            )
            language_node.add_child(pdf_node)
            language_node.add_child(audio_node)
            song_node.add_child(language_node)

        dict_activities = dict_content.get('Activities')
        activity_main_node = nodes.TopicNode(
            title="Activities",
            source_id="Activities",
            author="FolkDC",
            description="Activities",
            language=getlang_by_name("Activities")
        )
        for key in dict_activities:
            lst_activities = dict_activities[key]
            activity_node = nodes.TopicNode(
                title=key,
                source_id=key,
                author="FolkDC",
                description="Activities",
                language=getlang_by_name(key)
            )
            for dict_item in lst_activities:
                pdf_node = nodes.DocumentNode(
                    title=dict_item.get('pdf_name'),
                    source_id=f'{dict_item.get("pdf_name")}-PDF',
                    description='Activity',
                    language=getlang_by_name(dict_item.get('pdf_name')),
                    license=LICENSE,
                    files=[files.DocumentFile(dict_item.get('pdf_path'))]
                )
                activity_node.add_child(pdf_node)
            activity_main_node.add_child(activity_node)
        channel.add_child(activity_main_node)
        channel.add_child(song_node)
        return channel


# CLI
################################################################################
if __name__ == '__main__':
    # This code runs when sushichef.py is called from the command line
    chef = FolkDcChef()
    chef.main()
