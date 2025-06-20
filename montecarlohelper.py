import random
import numpy as np 
from scipy.stats import lognorm
from OCC.Core.gp import gp_Pnt
import time
import math

#np.set_printoptions(threshold=np.inf)
start = time.time()
# np.random.randint(1, 101, size=num_trials) generates an entire array of random values in one go.
def positive_negative_strike():
    if np.random.randint(1,101) <= 5:
        return 'positive'
    return 'negative'
    
def log_distribution(strike, sample_size=1):
    if strike == 'positive':
        sigma = 1.2
        mu = 35
    else:
        sigma = 0.484
        mu = 31.1
    samples = np.random.lognormal(mean=mu, sigma=sigma, size=sample_size)
    print(samples, strike)
    return (samples, strike)

def sphere_radius(tuple_sample_strike):
    if tuple_sample_strike[1] == 'positive':
        return 10*((tuple_sample_strike[0])**(0.65))
    return 10*((tuple_sample_strike[0])**(0.47))

def bulk_positive_negative_strikes(num_trials):
    # Vectorized generation of random integers from 1 to 100
    values = np.random.randint(1, 101, size=num_trials)
    
    # Boolean mask: True where the outcome is 'positive'
    positives = values <= 5

    # Use np.where to assign 'positive' or 'negative' based on the mask
    outcomes = np.where(positives, 'positive', 'negative')
    
    return outcomes


def bulk_log_distribution(strikes, pos_max=400, neg_max=400, pos_min= 4, neg_min=4):
    #We need to write predefined maximums and minimums
    strikes = np.asarray(strikes)
    
    # Output array for samples
    samples = np.empty_like(strikes, dtype=np.float64)

    # Masks
    pos_mask = strikes == 'positive'
    neg_mask = ~pos_mask

    mu_neg = np.log(31.1)
    mu_pos = np.log(35)
    # Sample for positive strikes
    pos_samples = np.random.lognormal(mean=mu_pos, sigma=1.2, size=pos_mask.sum())
    if pos_min is not None or pos_max is not None:
        pos_samples = np.clip(pos_samples, a_min=pos_min, a_max=pos_max)
    samples[pos_mask] = pos_samples

    # Sample for negative strikes
    neg_samples = np.random.lognormal(mean=mu_neg, sigma=0.484, size=neg_mask.sum())
    if neg_min is not None or neg_max is not None:
        neg_samples = np.clip(neg_samples, a_min=neg_min, a_max=neg_max)
    samples[neg_mask] = neg_samples


    return (samples, strikes)


def bulk_sphere_radii(samplesandstrikes):
    samples = np.asarray(samplesandstrikes[0])
    strikes = np.asarray(samplesandstrikes[1])

    # Create output array
    radii = np.empty_like(samples)

    # Masks
    pos_mask = strikes == 'positive'
    neg_mask = ~pos_mask

    # Apply vectorized formulas
    radii[pos_mask] = 10 * (samples[pos_mask] ** 0.65)
    radii[neg_mask] = 10 * (samples[neg_mask] ** 0.47)

    return radii

def random_xy_point_generation(x_bounds_tuple, y_bounds_tuple, num_trials):
    #tuple example
    #x_bounds = (-10, 10)
    #y_bounds = (-10, 10)

    # Generate random x, y points
    x_vals = np.random.uniform(x_bounds_tuple[0], x_bounds_tuple[1], num_trials)
    y_vals = np.random.uniform(y_bounds_tuple[0], y_bounds_tuple[1], num_trials)


    #WE NEED TO INCLUDE THIS FOR RADII OF SPHERE TO DO X,Y,Z GENERATION

    #Ask if the random point generation needs to be discrete or continuous

    # Stack into a (n_trials, 2) array of (x, y) pairs
    points_xy = np.column_stack((x_vals, y_vals))
    return list(map(lambda p: gp_Pnt(p[0], p[1], 0.0), points_xy))


def exponential_decay_for_distance(distance, A=1e7, k=1e-7):
    return A * (1 - np.exp(-k * distance))

def square_root(distance):
    return math.sqrt(distance)

def points_with_radii(x_bounds_tuple, y_bounds_tuple, radii, num_trials, z_max):
    x_vals = np.random.uniform(x_bounds_tuple[0], x_bounds_tuple[1], num_trials)
    y_vals = np.random.uniform(y_bounds_tuple[0], y_bounds_tuple[1], num_trials)

    #ADD ARG FOR MAX Z_HEIGHT 
    # Stack into a (n_trials, 2) array of (x, y) pairs
    points_xyz = np.column_stack((x_vals, y_vals, radii + z_max))
    return list(map(lambda p: gp_Pnt(p[0], p[1], p[2]), points_xyz))



def smart_move(distance, radius, factor=0.5, min_step=0.01):
    """
    Compute how much to move closer to target (radius), taking a fixed percentage step.
    Never overshoots. Stops when close enough.
    """
    delta = distance - radius
    if delta <= min_step:
        return  delta  # close enough, do final move CODE USED TO BE, return delta
    return max(delta * factor, min_step)

def collection_area(samples, x_bounds_tuple, y_bounds_tuple, count_for_shape):
    length = -x_bounds_tuple[0] + x_bounds_tuple[1]
    width = -y_bounds_tuple[0] + y_bounds_tuple[1]
    #print(length*width)
    return (count_for_shape/samples)*length*width



#need a function to take given points with z = 0 and 
def main():
    #print(sphere_radius(log_distribution(positive_negative_strike())))
    #print(bulk_sphere_radii(bulk_log_distribution(bulk_positive_negative_strikes(10000000))))
    #print(points_with_radii((-100,100),(-100,100),bulk_sphere_radii(bulk_log_distribution(bulk_positive_negative_strikes(10000000))),10000000)[:20])
   
    samples = 100
    radii = bulk_sphere_radii(bulk_log_distribution(bulk_positive_negative_strikes(samples)))
    #print(radii)
    #all samples how many are greater than 30 kA
    #50 percentile 30 kA
    radius = 50
    distance = 700
    counter = 0
    while (distance-radius) >= .1:
        moving = smart_move(distance, radius, factor=.9, min_step=.1)
        distance -= moving
        counter += 1
        print(counter)
        print(distance)


    


    end = time.time()
    print(f"Execution time: {end - start:.4f} seconds")

if __name__ == "__main__":
    main()