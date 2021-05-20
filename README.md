# NBA Simulation

## Implementation

Key parameters:
2 team indicators (HOU, MIA, BOS, BKN, etc) and a datetime object specifying the date of the game. The datetime object helps the data model identify the historical data to use and also the roster to query.


    from proj_envs import BallGame
    
    game = BallGame("HOU", "MIA", date=None)
    
    winners = []
    
    for i in range(100):
        game.play_game(verbose=False)
        #game.display_scores()
        winner = 1 if game.team_1.box_score["points"] >= game.team_2.box_score["points"] else 2
        winners.append(winner)
        
    win_prob_1 = len([i for i in winners if i == 1])/len(winners)
    win_prob_2 = 1 - win_prob_1
    
    print(win_prob_1)
    print(win_prob_2)    
