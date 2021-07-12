import os
import pandas as pd



class CustomDist:

    def __init__(self, dist_name):
        ''' '''
        dir_path = os.path.dirname(os.path.realpath(__file__))
        # print(dir_path)

        self.dist_df = pd.read_csv(f'{dir_path}/inputs/custom_dist/{dist_name}.csv')

        # print(self.dist_df.columns)

    def mean(self):
        return self.dist_df['mean'].tolist()

    def sd(self):
        return self.dist_df['sd'].tolist()
