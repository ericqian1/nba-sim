# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 20:12:22 2021

@author: tianz
"""

from proj_envs import BallGame

game = BallGame("BKN", "LAL", date=None)

winners = []

for i in range(50):
    game.play_game(verbose=False)
    game.display_scores()
    winner = 1 if game.team_1.box_score["points"] >= game.team_2.box_score["points"] else 2
    winners.append(winner)
    
win_prob_1 = len([i for i in winners if i == 1])/len(winners)
win_prob_2 = 1 - win_prob_1

print(win_prob_1)
print(win_prob_2)    


