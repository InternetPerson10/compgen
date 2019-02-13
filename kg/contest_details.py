import json
import os.path
import re

from .iutils import *

script_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(script_path, 'data', 'contest_defaults.json')) as f:
    defaults = json.load(f)

valid_keys = set(defaults) | {"comments", "extras"}

with open(os.path.join(script_path, 'data', 'contest_langs.json')) as f:
    langs = json.load(f)

def get_lang(lang):
    if isinstance(lang, str):
        lang = {"lang": lang}
    for key, value in langs.get(lang['lang'], {}).items():
        lang.setdefault(key, value)
    return lang

valid_contestcode = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$')

class ContestDetails(object):
    def __init__(self, details={}, source=None):
        self.details = details
        self.source = source
        self.relpath = os.path.dirname(os.path.abspath(source)) if source is not None else None

        # data validation
        for key in ['title', 'code', 'duration', 'scoreboard_freeze_length', 'site_password', 'problems', 'seating']:
            setattr(self, key, self.details.get(key, defaults.get(key)))

        if not (self.code and valid_contestcode.match(self.code)):
            raise ValueError("Invalid contest code: {}".format(rep(self.code)))

        for key, long_name in [
                    ('team', 'team'),
                    ('judge', 'judge'),
                    ('admin', 'administrator'),
                    ('leaderboard', 'leaderboard'),
                    ('feeder', 'feeder'),
                ]:
            key_list = key + 's'
            key_count = key + '_count'
            if key_list in self.details:
                if key_count in self.details:
                    raise ValueError("{} and {} cannot appear simultaneously".format(key_list, key_count))
                value_list = self.details[key_list]
                if isinstance(value_list, str): # open as a possible json file
                    with open(attach_relpath(self.relpath, value_list)) as f:
                        value_list = json.load(f)
                if not isinstance(value_list, list):
                    raise ValueError("{} must be a list: got {}".format(key_list, type(value_list)))
            else:
                value_count = self.details.get(key_count, defaults.get(key_count))
                if not isinstance(value_count, int):
                    raise ValueError("{} must be an int: got {}".format(key_count, type(value_count)))
                if value_count < 0:
                    raise ValueError("{} must be nonnegative: got {}".format(key_count, type(value_count)))
                value_list = [long_name + str(index) for index in range(1, value_count + 1)]

            if key == 'team':
                self.team_schools = self.get_team_schools(value_list)
                value_list = [team for ts in self.team_schools for team in ts['teams']]
                schools = [ts['school'] for ts in self.team_schools]
                if len(set(schools)) != len(schools):
                    raise ValueError("Duplicate school found!")

            if len(set(value_list)) != len(value_list):
                raise ValueError("Duplicate {} found!".format(key))
            setattr(self, key_list, value_list)

        # languages
        self.langs = [get_lang(lang) for lang in self.details.get('langs', defaults.get('langs'))]

        # check for extra keys
        for key in self.details:
            if key not in valid_keys:
                raise ValueError("Key {} invalid in contest.json. If you wish to add extra data, place it under 'comments' or 'extras'".format(repr(key)))

        super(ContestDetails, self).__init__()

    @classmethod
    def get_team_schools(cls, teamf):
        if not isinstance(teamf, list):
            raise ValueError("The team and school data must be a list: got {}".format(type(teamf)))
        team_schools = []
        schooli = 0
        for teamo in teamf:
            if isinstance(teamo, str):
                schooli += 1
                teamo = {
                    'school': schooli,
                    'teams': [teamo],
                }
            elif not isinstance(teamo['school'], str):
                raise ValueError("School must be a string, got {}".format(teamo['school']))
            team_schools.append(teamo)
        return team_schools

    @classmethod
    def from_loc(cls, loc):
        with open(loc) as f:
            return cls(json.load(f), source=loc)

    @property
    def rel_problems(self):
        return [attach_relpath(self.relpath, prob) for prob in self.problems]

    @property
    def rel_seating(self):
        return attach_relpath(self.relpath, self.seating)
    

    def serialize(self):
        ... # not implemented yet. returns a dict to be json'ed

