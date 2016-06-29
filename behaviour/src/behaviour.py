#!/usr/bin/env python
"""
Behaviour, S.O.S.VR
Developed by: Sajjad Azami
June 2016
"""

import actionlib
import roslib
import rospy
import smach
import smach_ros
import turtlesim
import math
import tf
from tf import TransformListener
import random
from actionlib_msgs.msg import GoalStatusArray
from nav_msgs.msg import OccupancyGrid
from move_base_msgs.msg import *
from smach_ros import ServiceState
from human_detector.msg import detectedobjectsMsg
import time
import threading

#####################################################
##################### VARIABLES #####################
goals_list = []  # goals given to robot will be appended to this
current_goal_status = 0  # goal status
# PENDING=0
# ACTIVE=1
# PREEMPTED=2
# SUCCEEDED=3
# ABORTED=4
# REJECTED=5
# PREEMPTING=6
# RECALLING=7
# RECALLED=8
# LOST=9
global_costmap = 0  # 2d array of costmap


################### END VARIABLES ###################
#####################################################

##################### FUNCTIONS #####################
#####################################################


# get current position of robot using tf translation
def get_current_position():
    listener = tf.TransformListener()
    rate = rospy.Rate(10.0)
    flag = True
    trans = 0
    while flag and not rospy.is_shutdown():
        try:
            (trans, rot) = listener.lookupTransform('/map', '/base_link', rospy.Time(0))
            rospy.loginfo(trans)
            flag = False
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            continue
    return trans


# random goal generator
# 0 for default
# 1 for NW
# 2 for NE
# 3 for SW
# 4 for SE
def get_random_goal(type):
    x, y, w, z = 0, 0, 0, 0
    if type == 0:
        x = random.uniform(-5.0, 5.0)
        y = random.uniform(-5.0, 5.0)
        w = random.uniform(-1.0, 1.0)
        z = random.uniform(-1.0, 1.0)
    if type == 1:  # NW
        x = random.uniform(-5.0, 0)
        y = random.uniform(0, 5.0)
        w = random.uniform(-1.0, 1.0)
        z = random.uniform(-1.0, 1.0)
    if type == 2:  # NE
        x = random.uniform(0.0, 5.0)
        y = random.uniform(0.0, 5.0)
        w = random.uniform(-1.0, 1.0)
        z = random.uniform(-1.0, 1.0)
    if type == 3:  # SW
        x = random.uniform(-5.0, 0)
        y = random.uniform(-5.0, 0)
        w = random.uniform(-1.0, 1.0)
        z = random.uniform(-1.0, 1.0)
    if type == 4:  # SE
        x = random.uniform(0, 5.0)
        y = random.uniform(-5.0, 0)
        w = random.uniform(-1.0, 1.0)
        z = random.uniform(-1.0, 1.0)

    return [x, y, 0, w, 0, 0, z]


# subscriber method callback from /move_base/status
def callback_goal_status(data):
    global current_goal_status
    current_goal_status = data.status_list[len(data.status_list) - 1].status


# subscriber method from /move_base/status
def listener_goal_status():
    rospy.Subscriber("move_base/status", GoalStatusArray, callback_goal_status)


# subscriber method callback from /move_base/global_costmap/costmap
def callback_global_costmap(data):
    global global_costmap
    global_costmap = data.data


# subscriber method from /move_base/global_costmap/costmap
def listener_global_costmap():
    rospy.Subscriber("/move_base/global_costmap/costmap", OccupancyGrid, callback_global_costmap)


# publishes goal on move_base/goal using SimpleActionClient
# inputs: position x, y, z, orientation w, x, y, z
def move_to(pos_x, pos_y, pos_z, ornt_w, ornt_x, ornt_y, ornt_z):
    # Simple Action Client
    sac = actionlib.SimpleActionClient('move_base', MoveBaseAction)

    # create goal
    goal = MoveBaseGoal()

    # set goal
    goal.target_pose.pose.position.x = pos_x
    goal.target_pose.pose.position.y = pos_y
    goal.target_pose.pose.orientation.w = ornt_w
    goal.target_pose.pose.orientation.z = ornt_z
    goal.target_pose.header.frame_id = 'odom'
    goal.target_pose.header.stamp = rospy.Time.now()

    # start listener
    sac.wait_for_server()

    # send goal
    sac.send_goal(goal)

    # finish
    # sac.wait_for_result()

    # print result
    goal_result = sac.get_result()


# TODO to be completedd
# publishes goal on move_base/goal using SimpleActionClient
# inputs: position x, y, z, orientation w, x, y, z
def frontier_exploration_publish_points():
    # Simple Action Client
    sac = actionlib.SimpleActionClient('move_base', ExploreTaskAction)


################### END FUNCTIONS ###################
#####################################################

####################### STATES ######################
#####################################################


# define Init state
class Init(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['toExplore', 'toRescue'])

    def execute(self, userdata):
        rospy.loginfo('Executing Init')
        return 'toExplore'


# define Init state
class WaitForVictim(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['victimSpotted', 'victimNotSpotted'])
        self.mutex = threading.Lock()
        self.found_recieved = False
        self.subscriber = rospy.Subscriber("/human_detection_result", detectedobjectsMsg, self.callback)
        # self.subscriber = rospy.Subscriber("/temp", uint8, self.callback)

    def callback(self, msg):
        self.mutex.acquire()
        if msg.found == 1:
            self.found_recieved = True
        self.mutex.release()

    def execute(self, userdata):
        rospy.loginfo('Executing WaitForVictim')
        # global current_goal_status
        # listener_goal_status()
        # # 3:Goal Reached
        # while current_goal_status != 3:
        #     self.mutex.acquire()
        #     listener_goal_status()
        #     if self.found_recieved:
        #         # found recieved
        #         return 'victimSpotted'
        #     self.mutex.release()
        #     time.sleep(.1)
        # # we didn't spotted victim in the 3 sec
        # return 'victimNotSpotted'
        time.sleep(10)
        return 'victimNotSpotted'


# define Explore state
class Explore(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['goalPublished', 'goalNotPublished'])
        # rospy.Subscriber("/move_base/global_costmap/costmap", OccupancyGrid, callback_global_costmap())

    def execute(self, userdata):
        rospy.loginfo('Executing state Explore')
        # goal_list_temp = [x, y, 0, w, 0, 0, x]  # Goal Format

        current_position = get_current_position()  # current translation of robot in an array[][]
        global global_costmap  # global costmap is stored here in an array[][]
        listener_global_costmap()

        goal_temp = get_random_goal(1)  # get random goal
        # TODO set goals to nearest costmap[][] = -1
        # TODO (Not Important for now) check for goal to make sure it is published using current_goal_status??

        goals_list.append(goal_temp)  # add goal to goal list(for further uses)
        move_to(goal_temp[0] + current_position[0], goal_temp[1] + current_position[1], goal_temp[2],
                goal_temp[3], goal_temp[4], goal_temp[5], goal_temp[6], )
        return 'goalPublished'


# define InitExplore state (Inner State)
class InitExplore(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['canExplore', 'cannotExplore'])

    def execute(self, userdata):
        rospy.loginfo('Executing InitExplore')
        return 'canExplore'


# define InitRescue state (Inner State)
class InitRescue(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['canRescue', 'cannotRescue'])

    def execute(self, userdata):
        rospy.loginfo('Executing state InitRescue')
        return 'canRescue'


# define Park state (Inner State)
class Park(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['parkSuccessful', 'parkFail'])
        self.mutex = threading.Lock()
        self.victim_side = 0
        self.subscriber = rospy.Subscriber("/human_detection_result", detectedobjectsMsg, self.callback)

    def callback(self, msg):
        self.mutex.acquire()
        self.victim_side = msg.lr
        self.mutex.release()

    def execute(self, userdata):
        rospy.loginfo('Executing Park')
        current_position = get_current_position()  # current translation of robot in an array[][]
        # goal_list_temp = [x, y, 0, w, 0, 0, x]  # Goal Format

        goal_temp = [x, y, 0, w, 0, 0, x]
        goals_list.append(goal_temp)  # add goal to goal list(for further uses)
        move_to(goal_temp[0] + current_position[0], goal_temp[1] + current_position[1], goal_temp[2],
                goal_temp[3], goal_temp[4], goal_temp[5], goal_temp[6], )

        return 'parkSuccessful'


# define Shutdown state (Inner State)
class Shutdown(smach.State):
    def __init__(self):
        smach.State.__init__(self)

    def execute(self, userdata):
        rospy.loginfo('Executing Shutdown')
        return 'SHUTDOWN'


# define PassTask state (Inner State)
class PassTask(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['canContinue', 'cannotContinue'])

    def execute(self, userdata):
        rospy.loginfo('Executing PassTask')
        return 'canContinue'


#################### END STATES #####################
#####################################################


def main():
    rospy.init_node('behaviour')
    sm = smach.StateMachine(
        outcomes=['SHUTDOWN'])

    with sm:
        smach.StateMachine.add('INIT', Init(),
                               transitions={'toRescue': 'INIT_RESCUE', 'toExplore': 'INIT_EXPLORE'})

        smach.StateMachine.add('INIT_RESCUE', InitRescue(),
                               transitions={'canRescue': 'PARK', 'cannotRescue': 'PASS_TASK'})

        smach.StateMachine.add('WAIT_FOR_VICTIM', WaitForVictim(),
                               transitions={'victimSpotted': 'PARK', 'victimNotSpotted': 'PASS_TASK'})

        smach.StateMachine.add('INIT_EXPLORE', InitExplore(),
                               transitions={'canExplore': 'EXPLORE', 'cannotExplore': 'SHUTDOWN'})

        smach.StateMachine.add('EXPLORE', Explore(),
                               transitions={'goalPublished': 'WAIT_FOR_VICTIM', 'goalNotPublished': 'INIT_EXPLORE'})

        smach.StateMachine.add('PARK', Park(),
                               transitions={'parkFail': 'PARK', 'parkSuccessful': 'SHUTDOWN'})

        smach.StateMachine.add('PASS_TASK', PassTask(),
                               transitions={'canContinue': 'INIT_EXPLORE', 'cannotContinue': 'SHUTDOWN'})

        sis = smach_ros.IntrospectionServer('Behavior', sm, '/SM_ROOT')
        sis.start()

        # Execute SMACH plan
        outcome = sm.execute()

        rospy.spin()
        sis.stop()


if __name__ == '__main__':
    main()
