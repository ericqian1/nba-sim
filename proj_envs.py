# -*- coding: utf-8 -*-
"""
Created on Sun Apr 25 21:14:32 2021

@author: tianz
"""

from assets import Team
from stats import flip, redist, choice
from utils import DataBase
import numpy as np


data = DataBase()


class BallGame():
    
    
    def __init__(self, team_name_1, team_name_2, date=None):
        
        self.team_name_1 = team_name_1
        self.team_name_2 = team_name_2
        self.team_desc = {1: team_name_1, 2: team_name_2}
        self.team_1 = Team(team_name_1, opponent=team_name_2, date=date)
        self.team_2 = Team(team_name_2, opponent=team_name_1, date=date)
        self.team_1.init_roster()
        self.team_2.init_roster()
        self.possession = None
        self.o_team = None
        self.d_team = None      
        self.first_possession = None
        self.verbose = False
        
        # State vars
        self.total_clock = 48 * 60
        self.quarter_clock = 12 * 60
        self.possession_clock = 24
        self.ball = None
        self.prev_ball = None
        self.new_ball = None
        
        
    def reverse_possession(self):
        self.possession = 1 if self.possession == 2 else 2
        
    
    def jump_ball(self):
        
        self.possession = 1 if flip() else 2
        self.first_possession = self.possession
        self.init_possession()


    def init_possession(self, time=24, assign_handler=True):
        self.possession_clock = min(time, self.quarter_clock)
        self.o_team = self.team_1 if self.possession == 1 else self.team_2
        self.d_team = self.team_1 if self.possession == 2 else self.team_2
        self.ball = self.o_team.ball_handler if assign_handler else self.ball
        
        statement = f"{self.o_team.name} starts with {time} on clock, {self.ball} handling"
        if self.verbose:
            print(statement)
            
        return


    def possession_increment(self):
        inc = np.random.choice(5) - 2 + self.o_team.roster_pace
        return inc
    
    def oob(self):
        self.o_team.recompute_roster()
        self.d_team.recompute_roster()
        statement = f"Roster changes, {self.o_team.name} subs in {self.o_team.on_field}\n"
        statement += f"Roster changes, {self.d_team.name} subs in {self.d_team.on_field}"
        if self.verbose:
            print(statement)
    
    def foul_action(self, shots):
        
        self.oob()        
        pts = 0
        for shot in range(shots):
            pts_now = self.o_team.players[self.ball].free_throws()
            self.o_team.box_score["points"] += pts_now      
            pts += pts_now
        statement = f"{self.ball} is fouled and shoots {shots} free throws, makes {pts} pts"
        
        if self.verbose:
            print(statement)
            
        if pts==0:
            self.assign_rb()
        else:
            self.reverse_possession()
            self.init_possession()
        
        return pts
    
    
    def turnover(self):
        statement = f"{self.ball} turns it over"
        if self.verbose:
            print(statement)

        self.reverse_possession()                
        self.init_possession()
    
            
    def action(self):
        
        # Actions:
        # -1: turnover
        # 0: pass
        # 2: 2p fga
        # 3: 3p fga
        time = self.possession_increment()
        self.possession_clock = max(0, self.possession_clock - time)
        fouled = False
        
        if self.possession_clock > 18:
            action = 0
        elif self.possession_clock == 1:
            action = -1        
        elif self.possession_clock <= 4:
            action = self.o_team.players[self.ball].choose_shot()
        else:
            action = self.o_team.players[self.ball].action()
        
        if action != -1 and action == 3:
            # Should hardly foul on a 3 
            fouled = np.random.rand() < self.o_team.players[self.ball].foul_pct/5
        else:
            fouled = np.random.rand() < self.o_team.players[self.ball].foul_pct            
            
        self.possession_clock = max(0, self.possession_clock - time)
        self.quarter_clock = max(0, self.quarter_clock - time)
        self.total_clock -= time
        
        if fouled and action != -1:
            if action == 0:
                self.d_team.pass_fouls += 1
                if self.d_team.pass_fouls > 4:
                    self.foul_action(2)
            else:
                self.foul_action(action)
            
        return action, fouled


    def assign_rb(self):
        orb_proba = self.o_team.roster_orb/self.o_team.roster_fga
        drb_proba = self.d_team.roster_drb/self.d_team.roster_fga
        reb_dist = redist([orb_proba, drb_proba])
        rb_team = choice([1, 2], probs=reb_dist)
        
        # For ORB            
        if rb_team == 1:
            self.ball = self.o_team.assign_rb("o")
            self.possession_clock = 14

        # For DRB
        elif rb_team == 2:
            self.ball = self.d_team.assign_rb("d")
            self.reverse_possession()                 
            self.init_possession(assign_handler=False)
            
        statement = f"Rebound, {self.o_team.name} gains ball"
        if self.verbose:
            print(statement)
        
        # Rebounds take 2 seconds
        self.possession_clock = max(0, self.possession_clock - 2)
        self.quarter_clock = max(0, self.quarter_clock - 2)
        self.total_clock -= 2
        
        
    def pass_action(self, fouled):
        
        # Successful pass, turnover
        if fouled:
            self.d_team.pass_fouls += 1
            if self.d_team.pass_fouls > 4:
                self.foul_action(2)
        else:
            to_probs = redist([self.o_team.players[self.ball].pass_success, self.d_team.roster_tov_pct])
            turnover = np.random.rand() > to_probs[0]
            
            if turnover:
                if np.random.rand() < .5:
                    self.oob()
                self.turnover()
            else:
                passing_players = [player for player in self.o_team.on_field if player != self.ball]
                probs = redist([self.o_team.players[player].usg for player in passing_players])
                ball = choice(passing_players, probs=probs)
                self.prev_ball = self.ball
                self.ball = ball
                
                statement = f"Pass successful, {self.prev_ball} passes to {self.ball}"
                if self.verbose:
                    print(statement)
            
    
    def shot_action(self, shot_val, fouled):
        
        discount = 0
        if fouled:
            discount = .3
        
        pts_shot = self.o_team.players[self.ball].shoot(score_type=shot_val, discount=discount)
        self.o_team.box_score["points"] += pts_shot
        
        if pts_shot == 0:
            statement = f"{self.ball} shoots a {shot_val}, misses"
        elif pts_shot > 0:
            statement = f"{self.ball} shoots a {shot_val}, makes"
        
        if self.verbose:
            print(statement)
            
        if pts_shot==0 and not fouled:
            # Blocking scenario
            if np.random.rand() < self.d_team.roster_bpg_pct:
                if self.verbose:
                    print("Shot blocked")
                if np.random.rand() < .7:
                    self.oob()
                    self.init_possession(14)
                elif np.random.rand() < .1:
                    self.init_possession(14)
                else:
                    self.reverse_possession()                
                    self.init_possession()                    
            else:
            # Else, assign rebound
                self.assign_rb()
        elif pts_shot > 0 and not fouled:
            self.reverse_possession()                
            self.init_possession()            
        elif pts_shot==0 and fouled:
            self.foul_action(shot_val) 
        elif pts_shot > 0 and fouled:
            self.foul_action(1) 
    
    
    def play_game(self, verbose=False):
        
        self.verbose = verbose
        self.team_1.box_score["points"] = 0
        self.team_2.box_score["points"] = 0
        
        self.team_1.init_roster()
        self.team_2.init_roster()
        self.possession = None
        self.o_team = None
        self.d_team = None      
        self.first_possession = None
        
        # State vars
        self.total_clock = 48 * 60
        self.quarter_clock = 12 * 60
        self.possession_clock = 24
        self.ball = None
        self.prev_ball = None
        self.new_ball = None

        
        self.jump_ball()
        quarter = 1
        
        while self.total_clock > 0:
            action, fouled = self.action()
            
            if action == -1:
                self.turnover()
            elif action == 0:
                self.pass_action(fouled)
            elif action == 2 or action == 3:
                self.shot_action(action, fouled)
            
            if self.quarter_clock == 0:
                quarter += 1
                self.quarter_clock = 12 * 60
                if quarter > 2:
                    self.reverse_possession()                
                    self.init_possession()
                else:
                    self.possession = self.first_possession
                    self.init_possession()
                    
    
    def display_scores(self):
        print(self.team_1.name, self.team_1.box_score["points"])
        print(self.team_2.name, self.team_2.box_score["points"])
