# -*- coding: utf-8 -*-
"""
Created on Thu Apr 22 19:31:09 2021

@author: tianz
"""

import numpy as np
np.random.seed(0)
from numpy import random
from utils import DataBase
from stats import gen_beta, update_beta, redist, choice
from scipy.stats import beta

data = DataBase()
    

class Player:
    
    
    def __init__(self, name, date=None):
        
        self.name = name
        self.date = date
        self.data = data.player_query(name, date=self.date, aggs=False)
        self.data_dict = data.player_query(name, date=self.date)
        self.fg_2_pct = self.data["FG2_PCT"].dropna().mean()
        self.fg_3_pct = self.data["FG3_PCT"].dropna().mean()
        
        if self.fg_2_pct > 0:
            self.fg_2_alpha, self.fg_2_beta = gen_beta(self.data["FG2_PCT"].dropna())
        else:
            self.fg_2_alpha, self.fg_2_beta = None, None
            
        if self.fg_3_pct > 0:
            self.fg_3_alpha, self.fg_3_beta= gen_beta(self.data["FG3_PCT"].dropna())
        else:
            self.fg_3_alpha, self.fg_3_beta = None, None            
        
        self.ppg = self.data_dict["PTS"] 
        self.apg = self.data_dict["AST"]
        self.tpg = self.data_dict["TO"]
        self.mpg = self.data_dict["MINS_PLAYED"]
        self.fg2a = self.data_dict["FG2A"]
        self.fg3a = self.data_dict["FG3A"]
        self.fg2m = self.data_dict["FG2M"]
        self.fg3m = self.data_dict["FG3M"]
        self.ft_pct = self.data_dict["FTM"]/self.data_dict["FTA"]
        self.fta = self.data_dict["FTA"]
        self.ftm = self.data_dict["FTM"]
        self.positions = []
        self.spg, self.bpg = self.data_dict["STL"], self.data_dict["BLK"]
        self.orpg, self.drpg = self.data_dict["OREB"], self.data_dict["DREB"]
        self.fouled_out = False
        self.fga = self.fg2a + self.fg3a
        self.fgm = self.fg2m + self.fg3m
        self.usg = (self.fga + self.apg + self.tpg + .44 * self.fta)/self.mpg
        self.o_usg = (self.fga + .44 * self.fta)/self.mpg
        self.foul_pct = (self.fta*.44 + 1)/((self.apg + self.tpg) * 8 + self.fga + self.fta * .44)
        self.pass_success = 1-(self.tpg)/(self.apg*8)
        self.box_score = {"points": 0,
                          "assists": 0,
                          "orebounds": 0, 
                          "drebounds": 0,                           
                          "steals": 0,
                          "blocks": 0,
                          "turnovers": 0,
                          "3pm": 0,
                          "2pm": 0,
                          "3pa": 0,
                          "2pa": 0,                          
                          "fouls": 0,
                          "ftm": 0,
                          "fta": 0}        
        
        
    def apply_beta_bayes(self, opponent_name, stat="FG2_PCT"):
            
        opp_query = data.player_query(self.name, date=self.date, opponent=opponent_name, aggs=False)
        opp_query = opp_query.fillna(0)
        total_games = len(opp_query)
        
        if stat == "FG2_PCT" and self.fg_2_pct > 0:
            N = opp_query["FG2A"].sum()/total_games
            x = opp_query["FG2M"].sum()/total_games
            
            if N==0 or total_games==0:
                return
            
            self.fg_2_alpha, self.fg_2_beta = update_beta(self.fg_2_alpha, self.fg_2_beta, N, x)
            
        if stat == "FG3_PCT" and self.fg_3_pct > 0:
            
            N = opp_query["FG3A"].sum()/total_games
            x = opp_query["FG3M"].sum()/total_games
            
            if N==0 or total_games==0:
                return 
            
            self.fg_2_alpha, self.fg_2_beta = update_beta(self.fg_2_alpha, self.fg_2_beta, N, x)
    
    
    def choose_shot(self):
        two = np.random.rand() < self.fg2a/self.fga
        return 2 if two else 3        
    
    
    def action(self):
        # 0 for pass, 2 and 3 for shoot values
        shoots = np.random.rand() < (self.fga)/((self.apg + self.tpg) * 8 + self.fga)
        if not shoots:
            return 0
        else:
            return self.choose_shot()
        

    def shoot(self, score_type=2, fg=None, discount=0):
        
        a = self.fg_2_alpha if score_type==2 else self.fg_3_alpha
        b = self.fg_2_beta if score_type==2 else self.fg_3_beta
        try:
            fg = beta.rvs(a, b)
        except:
            return 0 
        self.box_score[f"{score_type}pa"] += 1
        score = random.rand() < max(0, fg - discount)
        if score:
            self.box_score[f"{score_type}pm"] += score_type
        return score_type if score else 0
    
    
    def free_throws(self): 
        ft_points = 1 if random.rand() < self.ft_pct else 0
        return ft_points
        
    
    def pass_ball(self, probs):
        # Select who to pass to, 4 probability sets
        return np.random.choice(probs)
        
        
    def steal(self):
        self.box_score["steals"] += 1
    
    
    def block(self):
        self.box_score["blocks"] += 1

    
    def orb(self):
        self.box_score["orebounds"] += 1

        
    def drb(self):
        self.box_score["drebounds"] += 1        
        
        
    def assist(self):
        self.box_score["assists"] += 1

    
    def foul(self):
        self.box_score["fouls"] += 1
        self.fouled_out = True if self.box_score["fouls"] == 6 else False



class Team:
    
    
    def __init__(self, team_name, date=None, opponent=None, players=None):
        
        self.name = team_name
        self.roster = data.query_roster(team_name, date=date) 
        self.player_names = list(self.roster["name_join"])
        self.players = {}
        self.starters = []
        
        # Aggregate player stats
        self.pass_fouls = 0
        self.ppg = 0
        self.apg = 0
        self.tpg = 0
        self.orpg = 0
        self.drpg = 0
        self.fg2a = 0
        self.fg3a = 0
        self.fg3m = 0
        self.fg3a = 0 
        self.spg = 0
        self.bpg = 0
        self.fta = 0
        self.ftm = 0
        self.mpg = 0
        self.timeouts = 7
        self.on_field = []
    
        # Add players and define roster
        for i, row in self.roster.iterrows():
            player = row["name_join"]
            pos = row["position"]
            self.players[player] = Player(player, date)
            self.players[player].positions = [i for i in pos if i in ["G", "F", "C"]]
            
            self.ppg += self.players[player].ppg
            self.apg += self.players[player].apg
            self.tpg += self.players[player].tpg
            self.orpg += self.players[player].orpg
            self.drpg += self.players[player].drpg
            self.fg2a += self.players[player].fg2a
            self.fg3a += self.players[player].fg3a
            self.fg3m += self.players[player].fg3m
            self.fg3a += self.players[player].fg3a
            self.spg += self.players[player].spg
            self.bpg += self.players[player].bpg
            self.fta += self.players[player].fta
            self.ftm +=  self.players[player].ftm
            self.mpg +=  self.players[player].mpg
            
            if opponent:
                self.players[player].apply_beta_bayes( opponent, stat="FG2_PCT")
                self.players[player].apply_beta_bayes( opponent, stat="FG3_PCT")
            
                                    
        self.box_score = {"points": 0,
                          "assists": 0,
                          "orebounds": 0, 
                          "drebounds": 0,                           
                          "steals": 0,
                          "blocks": 0,
                          "turnovers": 0,
                          "3pm": 0,
                          "2pm": 0,
                          "3pa": 0,
                          "2pa": 0,                          
                          "fouls": 0,
                          "ftm": 0,
                          "fta": 0}
        
        self.fga = self.fg2a + self.fg3a
    
    
    def _validate_roster(self):
        guards = 0
        forwards = 0
        centers = 0
        for player in self.on_field:
            if "F" in self.players[player].positions:
                forwards += 1
            if "C" in self.players[player].positions:
                centers += 1
            if "G" in self.players[player].positions:
                guards += 1
        return guards >= 2 and forwards >= 2
        
        
    def roster_stats(self):
        self.roster_fga = sum([self.players[player].fga for player in self.on_field])
        self.roster_fgm = sum([self.players[player].fgm for player in self.on_field])        
        self.roster_drb = sum([self.players[player].drpg for player in self.on_field])          
        self.roster_orb = sum([self.players[player].orpg for player in self.on_field])                            
        self.roster_spg = sum([self.players[player].spg for player in self.on_field])           
        self.roster_bpg = sum([self.players[player].bpg for player in self.on_field])                                                      
        self.roster_mpg = sum([self.players[player].mpg for player in self.on_field])                                                      
        self.roster_usg = sum([self.players[player].usg for player in self.on_field])     
        self.roster_apg = sum([self.players[player].apg for player in self.on_field])                                                                                                       
        self.roster_tpg = sum([self.players[player].tpg for player in self.on_field])   
        self.roster_fta = sum([self.players[player].fta for player in self.on_field])          
        
        self.ball_handler = self.on_field[np.argmax([self.players[player].usg for player in self.on_field])]                                                   
        self.roster_bpg_pct = self.roster_bpg/(self.roster_fga - self.roster_fgm)
        self.roster_tov_pct = self.roster_spg*2/((self.apg + self.tpg) * 8 )
        self.roster_pace = 24/(((self.roster_apg + self.roster_tpg)*8 ) / (self.roster_fga + self.roster_fta * .44)) 

        
    def recompute_roster(self, filt=10):
        validation = False
        # If under 10 min per game youre probably playing garbage time
        mins_dict = {player: self.players[player].mpg for player in self.player_names 
                     if self.players[player].mpg > filt}
        player_list = list(mins_dict.keys())
        mins_list = redist(np.array(list(mins_dict.values())))

        while not validation:
            self.on_field = choice(player_list, mins_list, size=5)
            validation = self._validate_roster()
        self.roster_stats()


    def init_roster(self):
        mins_dict = {player: self.players[player].mpg for player in self.player_names}
        sorted_dict = dict(sorted(mins_dict.items(), key=lambda item: item[1], reverse=True))
        self.on_field = [player for i, (player, mpg) in enumerate(sorted_dict.items())  if i<5]   
        self.roster_stats()
    
    
    def assign_rb(self, rtype = "d"):
        
        if rtype == "o":
            probs = [self.players[player].orpg/self.roster_orb for player in self.on_field]
        else:
            probs = [self.players[player].drpg/self.roster_drb for player in self.on_field]
        
        return choice(self.on_field, probs=probs)
