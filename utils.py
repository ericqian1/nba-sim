import pandas as pd
from datetime import datetime, time

def home_away(row):
    if row['TEAM_ID'] == row['HOME_TEAM_ID']:
        return 'Home'
    else:
        return 'Away'

def opponent_id(row):
    if row['TEAM_ID'] == row['HOME_TEAM_ID']:
        return row['VISITOR_TEAM_ID']
    else:
        return row['HOME_TEAM_ID']

def mins_played(row):
    if row['MINS_PLAYED'] == 'nan':
        return 0
    else:
        return float(row['MINS_PLAYED'])
    
def simple_str(x):
    update = ''.join(x.split()[:2])
    return ''.join(filter(str.isalnum, update))


class DataBase():
    
    
    def __init__(self):
        
        df_games = pd.read_csv('Project_Data/NBA_Data_Games.csv')
        df_game_details = pd.read_csv('Project_Data/NBA_Data_Game_Details.csv')
    
        df_years = df_games[['GAME_DATE_EST', 'GAME_ID', 'SEASON', 'HOME_TEAM_ID', 'VISITOR_TEAM_ID']]
        df_merged = df_game_details.merge(df_years, how = 'left', left_on = 'GAME_ID', right_on = 'GAME_ID')
        df_merged['MINS_PLAYED'] = df_merged['MIN'].str.split(":").str[0]
        df_merged['MINS_PLAYED'] = df_merged['MINS_PLAYED'].astype(str)
    
        # last 2 years only
        df_merged = df_merged[df_merged['SEASON'].isin([2021, 2020, 2019])]
    
        df_merged['FIELD'] = df_merged.apply(home_away, axis = 1)
        df_merged['OPPONENT_TEAM_ID'] = df_merged.apply(opponent_id, axis = 1)
        df_merged['MINS_PLAYED'] = df_merged.apply(mins_played, axis = 1)
        
        df_NBA_teams = pd.read_csv('Project_Data/NBA_Data_Teams.csv')
        
        df_teams_ID = df_NBA_teams[['TEAM_ID', 'ABBREVIATION']]
        df_merged = df_merged.merge(df_teams_ID, how = 'left', left_on = 'OPPONENT_TEAM_ID', right_on = 'TEAM_ID', copy = False)
        
        df_merged.drop(["TEAM_ID_y"], axis = 1, inplace = True)
        df_merged.rename(columns = {"TEAM_ID_x" : "TEAM_ID", "ABBREVIATION": "OPPONENT"}, inplace = True)
        
        df_merged["FG2A"] = df_merged["FGA"] - df_merged["FG3A"]
        df_merged["FG2M"] = df_merged["FGM"] - df_merged["FG3M"]
     
        df_merged["FG2_PCT"] = df_merged["FG2M"]/df_merged["FG2A"]
        df_merged["GAME_DATE_EST"] = pd.to_datetime(df_merged["GAME_DATE_EST"])
        
        self.df_merged = df_merged        
        self.stats_lst = ['PTS', 'REB', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TO','FG2M', 
                     'FG2A', 'FG3A', 'FG3M', 'FTM','FTA', 'MINS_PLAYED', 'FG2_PCT', 'FG3_PCT']
        self.team_stats = ['PTS', 'REB', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TO','FG2M', 
                     'FG2A', 'FG3A', 'FG3M', 'FTM','FTA']
        self.player_data = pd.read_csv("Project_Data/player_data.csv")
        self.player_data["name_join"] = self.player_data["name"].apply(lambda x: simple_str(x))
        self.df_merged["name_join"] = self.df_merged["PLAYER_NAME"].apply(lambda x: simple_str(x))
        
    
    def query(self, fields, date=None):
        df_filt = self.df_merged.copy()
        for field, val in fields.items():
            df_filt = df_filt[df_filt[field] == val]
            
        if date:
            df_filt = df_filt[df_filt["GAME_DATE_EST"] < date]
        return df_filt
    
        
    def player_query(self, player_name, date=None, field=None, opponent=None, aggs=True):
        fields = {"name_join": player_name}
        if field:
            fields["FIELD"] = field
        if opponent:
            fields["OPPONENT"] = opponent
            
        df_player = self.query(fields, date=None)
        
        if aggs:
            return df_player[self.stats_lst].mean().to_dict()
        else:
            return df_player
            
    
    def team_query(self, team_name, field=None, opponent=None, aggs=True):
        fields = {"TEAM_ABBREVIATION": team_name}
        if field:
            fields["FIELD"] = field
        if opponent:
            fields["OPPONENT"] = opponent
            
        df_team = self.query(fields).groupby(["GAME_ID"])[self.team_stats].sum()
        df_team["FG2_PCT"] = df_team["FG2M"]/df_team["FG2A"]
        df_team["FG3_PCT"] = df_team["FG3M"]/df_team["FG3A"]
        
        if aggs:
            return df_team.mean().to_dict()
        else:
            return df_team

    
    def query_roster(self, team_name, date=None):
        df_team = self.df_merged[self.df_merged["TEAM_ABBREVIATION"] == team_name]
        date = date if date else df_team["GAME_DATE_EST"].max()
        if date:
            df_team = df_team[(df_team['GAME_DATE_EST'] == date)]
        roster = df_team[df_team["MINS_PLAYED"] > 0].groupby('PLAYER_NAME')[
                'MINS_PLAYED'].last().sort_values(ascending = False).to_dict()
        roster_simple = [simple_str(i) for i in roster]
        roster_data = self.player_data[self.player_data["name_join"].isin(roster_simple)]
        roster_data = roster_data[["name_join", "position"]]
        roster_out = [i for i in roster_simple if i not in roster_data["name_join"].values]
        
        return roster_data.append(pd.DataFrame({"name_join": [i for i in roster_out],
                                                "position": ["F-G-P" for i in roster_out]}))
    