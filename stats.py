# -*- coding: utf-8 -*-
"""
Created on Sat Apr 24 12:26:55 2021

@author: tianz
"""

import numpy as np
from numpy import random
import pandas as pd
from scipy.stats import beta


def redist(x):
    if isinstance(x, list):
        x = np.array(x)
    x_new = x/x.sum()
    return x_new


def choice(choices, probs, size=1, replace=False):
    dec = np.random.choice(choices, size=size, replace=replace, p=probs)
    if len(dec)== 1:
        dec = dec[0]
    return dec
    
    
def flip(prob=.5):
    return random.rand() < prob


def gen_beta(data):
    # Param 0 is alpha
    # Param 1 is b1
    # Param 2 is loc
    data = data[~np.isnan(data)]
    data = np.array([.01 if i==0 else .99 if i==1 else i for i in data])
    beta_params = beta.fit(data, floc=0.,fscale=1.)
    return beta_params[0], beta_params[1]


def update_beta(a, b, N, x):
    return a+x, b+N-x
