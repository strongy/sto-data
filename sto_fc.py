#!/usr/bin/python

import json, collections, unicodecsv as csv, sys, dateutil.parser, datetime, copy

# note the dependencies on dateutil.parser (v1.x series, because this is Python 2) and unicodecsv

class Fleet(object):
    '''Represents a fleet.  Contains individual accounts, which contains characters.  Has convenience functions to operate over list of members'''
    def __init__(self, name):
        self.name = name
        self.accounts = []
        self.account_name_index = {}
        
    @property
    def num_characters(self):
        n = 0
        for account in self.accounts:
            n += len(account.characters)
        return n

    def sort(self):
        self.accounts.sort(cmp=lambda x, y: cmp(x.fc, y.fc), reverse=True)
        
    def sort_by_last_login(self):
        self.accounts.sort(key=lambda account: account.last_logged_out, reverse=True)
        
    def get_accounts_within_n_days(self, d):
        result = []
        self.sort_by_last_login()
        for account in self.accounts:
            if account.last_logged_out >= d:
                result.append(account)
        return result
    
    def load_from_holding_dict(self, holding_d):
        holding_name = holding_d.get("typename")
        for donorstat in holding_d.get("donationstats"):
            character_name, account_name = Account.parse_name(donorstat.get("displayname"))
            contribution = donorstat.get("contribution")
            account = None
            character = None
            if account_name not in self.account_name_index:
                account = Account(name=account_name)
                self.accounts.append(account)
                self.account_name_index[account_name] = account
            else:
                account = self.account_name_index[account_name]
            if character_name not in account.character_name_index:
                character = Character(name=character_name, account_name=account.name)
                account.characters.append(character)
                account.character_name_index[character_name] = character
            else:
                character = account.character_name_index[character_name]
            character.fc_dict[holding_name] += contribution
            
    def load_from_members_array(self, members_array):
        for member in members_array:
            character_name = member["name"]
            account_name = member["publicaccountname"][1:]
            rank = member["officerrank"]
            last_logged_out = dateutil.parser.parse(member["logouttime"])
            if account_name not in self.account_name_index:
                account = Account(name=account_name)
                self.accounts.append(account)
                self.account_name_index[account_name] = account
            else:
                account = self.account_name_index[account_name]
            if character_name not in account.character_name_index:
                character = Character(name=character_name, account_name=account.name)
                account.characters.append(character)
                account.character_name_index[character_name] = character
            else:
                character = account.character_name_index[character_name]
                #print "Found character %s" %(character_name)
            character.rank = rank
            character.last_logged_out = last_logged_out
            #print "Appending character %s%s %s" %(character.name, account.name, character.rank)
    
    @classmethod
    def get_account_by_name(self, name):
        return self.account_name_index.get("name")
    
class Character(object):
    def __init__(self, name, account_name):
        self.name = name
        self.account_name = account_name
        self.fc_dict = collections.defaultdict(int)
        self.last_logged_out = None
        self.rank = ""
    
    @property
    def total_fc(self):
        return sum(self.fc_dict.values())

class Account(object):
    def __init__(self, name):
        self.name = name
        self.characters = []
        self.character_name_index = {}
    
    def __repr__(self):
        return "<%s %s>" % (self.name, self.last_logged_out.isoformat() if self.last_logged_out else "None")
        
    @classmethod
    def parse_name(cls, namestring):
        name_r = namestring.strip().split("@")
        if len(name_r) >= 2:
            return name_r[0], name_r[1]
        return "", ""
        
    @property
    def fc(self):
        return sum([c.total_fc for c in self.characters])

    def fc_for_holding(self, holding):
        return sum([c.fc_dict[holding] for c in account.characters])
    
    @property
    def fc_by_holding(self):
        holdings = collections.defaultdict(int)
        for c in self.characters:
            for h in c.fc_dict.keys():
                holdings[h] += c.fc_dict[h]
        return holdings
    
    @property
    def last_logged_out(self):
        chars = list(self.characters)
        chars.sort(key=lambda character: character.last_logged_out if character.last_logged_out else datetime.datetime(1999, 1, 1, 1, 1, 1, tzinfo=dateutil.tz.tzutc()), reverse=True)
        return chars[0].last_logged_out
        
    @property
    def rank(self):
        return self.characters[0].rank
        
class GrandFleet(Fleet):
    '''Grand fleets are fleets across factions'''
    
    def __init__(self, name, fleets):
        '''takes a list of fleets as constructor, and merges all characters into their accounts'''
        super(GrandFleet, self).__init__(name=name)
        for fleet in fleets:
            for account in fleet.accounts:
                if account.name in self.account_name_index:
                    # account already exists: merge characters
                    target_account = self.account_name_index[account.name]
                    for character in account.characters:
                        if character.name not in target_account.character_name_index:
                            target_account.characters.append(character)
                            target_account.character_name_index[character.name] = character
                        else:
                            target_account.character_name_index[character.name+"|"+fleet.name] = character
                            #raise ValueError("duplicate character names %s %s" % (character.name, target_account.name))
                else:
                    # add to accounts list and index
                    grand_account = copy.deepcopy(account)
                    self.accounts.append(grand_account)
                    self.account_name_index[account.name] = grand_account
                    
                    
def load_holdings_data_from_json(path_to_json, fleet_name):
    data = open(path_to_json, "rb").read()
    if path_to_json.endswith(".har"):
        har_file = json.loads(data)
        entries = har_file['log']['entries']
        for e in entries:
            if e["response"]["content"].get("text") and e["response"]["content"]["text"].startswith("5:::{\"name\":\"Proxy_GroupProject\""):
                data = e["response"]["content"]["text"]
                break
    if not data.startswith("{"):
        i = data.index("{") # assume we'll find a {, otherwise this isn't even json
        data = data[i:]
    fleet_json = json.loads(data)
    fleet_holdings = []
    try:
        fleet_holdings = fleet_json['args'][0]['container']['states']
        return fleet_holdings
    except:
        raise ValueError("Failed to locate fleet holdings array. The JSON format may have changed, or the JSON given is not the actual fleet holdings data")
        return []

def load_holdings_from_json(path_to_json, fleet_name="Fleet"):
    fleet_holdings = load_holdings_data_from_json(path_to_json, fleet_name)
    fleet = Fleet(name=fleet_name)
    for holding in fleet_holdings:
        fleet.load_from_holding_dict(holding)
    return fleet


def load_fleet_members_from_guild_data(path_to_json, fleet_name):
    data = open(path_to_json, "rb").read()
    if path_to_json.endswith(".har"):
        har_file = json.loads(data)
        entries = har_file['log']['entries']
        for e in entries:
            if e["response"]["content"].get("text") and e["response"]["content"]["text"].startswith('5:::{"name":"Proxy_Guild'):
                data = e["response"]["content"]["text"]
                break
    if not data.startswith("{"):
        i = data.index("{") # assume we'll find a {, otherwise this isn't even json
        data = data[i:]
    fleet_json = json.loads(data)
    fleet_holdings = []
    try:
        fleet_members = fleet_json['args'][0]['container']['members']
        return fleet_members
    except:
        raise ValueError("Failed to locate fleet members array. The JSON format may have changed, or the JSON given is not the actual fleet members data")
        return []

def load_fleet_from_guild_data(path_to_json, fleet_name="Fleet"):
    '''this loads the guild roster instead of the contrib roster'''
    fleet_members = load_fleet_members_from_guild_data(path_to_json, fleet_name=fleet_name)
    fleet = Fleet(name=fleet_name)
    fleet.load_from_members_array(fleet_members)
    return fleet

def output_lfc(path_to_json, fleet_name, output_path):
    fleet = load_holdings_from_json(path_to_json, fleet_name)
    fleet.sort()
    with open(output_path, 'wb') as csvfile:
        cwriter = csv.writer(csvfile)
        for account in fleet.accounts:
            cwriter.writerow([account.name, account.fc])
            
def output_promotion_list(rank_contrib_paired_files, grand_fleet_name, output_path):
    '''rank_contrib pair files are a list of tuples, each tuple being (path_to_roster, path_to_contribs, fleet_name)'''
    fleets = []
    for fleet_files in rank_contrib_paired_files:
        path_to_roster = fleet_files[0]
        path_to_contribs = fleet_files[1]
        fleet_name = fleet_files[2]
        fleet = load_holdings_from_json(path_to_contribs, fleet_name)
        fleet_members = load_fleet_members_from_guild_data(path_to_roster, fleet_name)
        fleet.load_from_members_array(fleet_members)
        fleets.append(fleet)
    grand_fleet = GrandFleet(grand_fleet_name, fleets)
    grand_fleet.sort()
    with open(output_path, 'wb') as csvfile:
        cwriter = csv.writer(csvfile)
        for account in grand_fleet.accounts:
            cwriter.writerow([account.name, account.rank, account.fc])
            
def output_lfc_diff_using_csv(path_to_csv_earlier, path_to_csv_later, output_path):
    fleet_time_a = {}
    fleet_time_b = {}
    fleet_diff = {}
    with open(path_to_csv_earlier, 'rUb') as csvfile:
        reader = csv.reader(csvfile, errors='ignore')
        for row in reader:
            if len(row) >= 2:
                fleet_time_a[row[0].strip()] = long(row[1].strip())
    with open(path_to_csv_later, 'rUb') as csvfile:
        reader = csv.reader(csvfile, errors='ignore')
        for row in reader:
            if len(row) >= 2:
                fleet_time_b[row[0].strip()] = long(row[1].strip())
    for account_name in fleet_time_b.keys():
        if account_name in fleet_time_a:
            lfc_diff = fleet_time_b[account_name] - fleet_time_a[account_name]
        else:
            lfc_diff = fleet_time_b[account_name]
        if lfc_diff > 0:
            fleet_diff[account_name] = lfc_diff
    fleet_diff_output = fleet_diff.items()
    fleet_diff_output.sort(key=lambda account_tuple: account_tuple[1], reverse=True)
    with open(output_path, 'wb') as csvfile:
        cwriter = csv.writer(csvfile)
        for account_tuple in fleet_diff_output:
            cwriter.writerow(account_tuple)
    #return diff


#def output_lfc_by_holding(path_to_json, fleet_name, output_path):
#    fleet = load_holdings_from_json(path_to_json, fleet_name)
#    fleet.sort()
#    with open(output_path, 'wb') as csvfile:
#        cwriter = csv.writer(csvfile)
#        for account in fleet.accounts:
#            cwriter.writerow([account.name, account.fc])

if __name__ == "__main__":
    # #output_promotion_list([("/Users/foo/Desktop/coa/coa-guildroster-0117014.txt", "/Users/foo/Desktop/coa/20140118/coa.json", "COA"), ("/Users/foo/Desktop/coa/hoa-guildroster-0118014.txt", "/Users/foo/Desktop/coa/20140118/hoa.json", "HOA")], "Athena", "/tmp/grand_ranks.csv")
    if len(sys.argv) < 4:
        print "Usage: python sto_fc.py <path_to_json_or_har> <fleet_name> <path_for_csv>\nExample: python sto_fc.py /Users/foo/tmp/gateway.har COA /tmp/coa.csv"
        sys.exit(-1)
    output_lfc(sys.argv[1], sys.argv[2], sys.argv[3])
    #output_lfc_diff_using_csv(sys.argv[1], sys.argv[2], sys.argv[3])
