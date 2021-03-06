from spike import PrimeHub, LightMatrix, Button, StatusLight, ForceSensor, MotionSensor, Speaker, ColorSensor, App, DistanceSensor, Motor, MotorPair
from spike.control import wait_for_seconds, wait_until, Timer
from math import *
import time

# establish port connections
hub = PrimeHub()
motors = MotorPair('C', 'D')
light_a = ColorSensor('A')
light_b = ColorSensor('B')
arm_motor = Motor('E')

# speed configuration
speed = 60
maneuvering_speed = 50
high_maneuvering_speed = 20

# other configuration
rgb_margin = 0.05 * 1024 # (how much rgb values may differ in order for it to be interpreted as grayscale)


# -- Line Guidance --

class LineGuidance:
    # reflection calibration
    min_light = 20 # (black)
    max_light = 98 # (white)

    def initialize(self):
        # calibrate lights

        # max_light / white
        hub.left_button.wait_until_pressed()
        self.max_light = light_a.get_reflected_light()
        hub.speaker.beep(65, 0.5)

        # min_light / black
        hub.left_button.wait_until_released()
        self.min_light = light_a.get_reflected_light()
        hub.speaker.beep(70, 0.5)

    instructions = []

    def drive(self):
        #print("drive")
        self.instructions.append(("drive",))

    def drive_and_take_crossing(self, crossing_target):
        #print("drive and take crossing " + str(crossing_target))
        self.instructions.append(("drive_and_take_crossing", str(crossing_target)))

    def drive_to_crossing(self, crossing_target):
        #print("drive to crossing " + str(crossing_target))
        self.instructions.append(("drive_to_crossing", str(crossing_target)))

    def drive_to_white(self):
        #print("drive to white")
        self.instructions.append(("drive_to_white",))

    def switch_to_lane(self, new_lane): # new_lane = 'A' or 'B'
        #print("switching to lane " + new_lane)
        self.instructions.append(("switch_to_lane", new_lane))

    def manually_switch_to_lane(self, new_lane): # new_lane = 'A' or 'B'
        #print("manually switching to lane " + new_lane)
        self.instructions.append(("manually_switch_to_lane", new_lane))

    def drive_for(self, seconds):
        #print("driving for (s) " + str(seconds))
        self.instructions.append(("drive_for", seconds))

    def run(self):
        self.crossings_left = -1
        for instruction in self.instructions:
            self.execute_instruction(instruction)
        self.instructions = []

    light_pr = light_b
    light_sc = light_a
    invert_steering = True

    crossings_left = -1
    lastly_crossing = False
    crossing_do_turn = False

    stop_at_white = False

    start_time = -1
    time_target = -1

    sc_on_track_start = -1

    def execute_instruction(self, instruction):
        print("executing instruction: " + str(instruction))

        # ----- drive -----
        instruction_name = instruction[0]
        #print("instruction name: " + str(instruction_name))
        length = len(instruction)
        #print("length: " + str(length))
        if instruction_name == "drive" and length == 1:
            #print("driving ...")
            while True:

                light_pr_percent = (self.light_pr.get_reflected_light() - self.min_light) / (self.max_light - self.min_light)
                light_sc_percent = (self.light_sc.get_reflected_light() - self.min_light) / (self.max_light - self.min_light)

                if self.stop_at_white and light_sc_percent >= 0.93:
                    self.stop_at_white = False
                    lastly_crossing = False
                    motors.stop()
                    return

                currently_crossing = self.light_sc.get_color() == "black"
                if currently_crossing:
                    hub.status_light.on("green")
                else:
                    hub.status_light.on("blue")
                if self.lastly_crossing != currently_crossing:
                    if currently_crossing:
                        motors.stop()
                        hub.speaker.start_beep(60)
                        self.crossings_left = self.crossings_left - 1
                        if self.crossings_left == 0:

                            if self.crossing_do_turn:
                                former_light_pr = self.light_pr
                                former_light_sc = self.light_sc
                                self.light_pr = former_light_sc
                                self.light_sc = former_light_pr
                                self.invert_steering = not self.invert_steering
                                while True:
                                    motors.start_tank_at_power(int(high_maneuvering_speed/2), int(high_maneuvering_speed*2))
                                    former_light_sc_percent = (former_light_sc.get_reflected_light() - self.min_light) / (self.max_light - self.min_light)
                                    if former_light_sc_percent > 0.8:
                                        break

                            crossings_left = -1
                            lastly_crossing = False
                            crossing_do_turn = False
                            hub.speaker.stop()
                            break

                    else:
                        hub.speaker.stop()

                    self.lastly_crossing = currently_crossing

                steering = (light_pr_percent - 0.5) * 100
                dynamic_speed = speed - ( abs(steering)/100 * (speed - maneuvering_speed) )
                if self.invert_steering:
                    steering = -steering
                motors.start_at_power(int(dynamic_speed), int(steering))

                if self.time_target != -1:
                    if self.start_time == -1:
                        self.start_time = time.time()
                    if time.time() >= (self.start_time + self.time_target):
                        self.time_target = -1
                        self.start_time = -1
                        motors.stop()
                        break
            print("... done")


        # ----- drive and take crossing -----
        if instruction_name == "drive_and_take_crossing" and length == 2:
            self.crossings_left = int(instruction[1])
            self.crossing_do_turn = True
            print("driving and taking crossing " + str(self.crossings_left) + " ...")
            self.execute_instruction(("drive",))

        # ----- drive to crossing -----
        if instruction_name == "drive_to_crossing" and length == 2:
            self.crossings_left = int(instruction[1])
            self.crossing_do_turn = False
            print("driving to crossing " + str(self.crossings_left) + " ...")
            self.execute_instruction(("drive",))

        # ----- drive for -----
        if instruction_name == "drive_for" and length == 2:
            self.time_target = int(instruction[1])
            print("driving for " + str(self.time_target) + " ...")
            self.execute_instruction(("drive",))

        # ----- switch to lane -----
        if instruction_name == "switch_to_lane" and length == 2:
            new_lane = instruction[1]
            print("switching to lane " + new_lane + " ...")
            old_light_pr = self.light_pr
            old_light_sc = self.light_sc
            print("is A")
            self.light_pr = light_a
            self.light_sc = light_b
            self.invert_steering = False
            if new_lane == "B":
                print("is B")
                self.light_pr = light_b
                self.light_sc = light_a
                self.invert_steering = True

            start_time = time.time()
            #print("start time: " + str(start_time))
            while True:
                if new_lane == "A":
                    #print("A...")
                    motors.start_tank_at_power(maneuvering_speed, int(maneuvering_speed * 0.05))
                else:
                    #print("B...")
                    motors.start_tank_at_power(int(maneuvering_speed * 0.05), maneuvering_speed)
                if self.light_pr.get_color() == "black":
                    #print("saw black")
                    motors.stop()
                    break
            #print("current time: " + str(time.time()))
            #print("start time: " + str(start_time))
            duration = time.time() - start_time
            duration = 1    #######################
            #print("duration: " + str(duration))
            new_time = duration * 0.8
            #print("new time: " + str(new_time))
            start_time = time.time()
            #print("start time: " + str(start_time))
            if new_lane == "B":
                #print("B...")
                motors.move_tank(new_time, unit="seconds", left_speed=maneuvering_speed, right_speed=int(maneuvering_speed * 0.05))
            else:
                #print("A...")
                motors.move_tank(new_time, unit="seconds", left_speed=int(maneuvering_speed * 0.05), right_speed=maneuvering_speed)
            #while True:
            #    if new_lane == "B":
            #        print("B...")
            #        motors.start_tank_at_power(maneuvering_speed, int(maneuvering_speed * 0.05))
            #    else:
            #        print("A...")
            #        motors.start_tank_at_power(int(maneuvering_speed * 0.05), maneuvering_speed)
            #    if time.time() - start_time >= new_time:
            #        print("time over")
            #        motors.stop()
            #        break
            #print("realigned")
            print("... done")

        # ----- manually switch to lane -----
        if instruction_name == "manually_switch_to_lane" and length == 2:
            new_lane = instruction[1]
            print("manually switching to lane " + new_lane + " ...")
            #print("is A")
            self.light_pr = light_a
            self.light_sc = light_b
            self.invert_steering = False
            if new_lane == "B":
                #print("is B")
                self.light_pr = light_b
                self.light_sc = light_a
                self.invert_steering = True
            print("... done")

        # ----- drive to white -----
        if instruction_name == "drive_to_white" and length == 1:
            print("driving to white...")
            self.stop_at_white = True
            self.execute_instruction(("drive",))


# -- Arm Control --

class ArmControl:

    arm_down = 10
    arm_mid = 40
    arm_up = 100

    def down(self):
        arm_motor.run_to_position(self.arm_down)
        print("down")

    def mid(self):
        arm_motor.run_to_position(self.arm_mid)
        print("mid")

    def up(self):
        arm_motor.run_to_position(self.arm_up)
        print("up")

    def calibrate(self):
        hub.right_button.wait_until_pressed()
        arm_motor.run_to_position(0)
        print("calibrating arm...")
        wait_for_seconds(1)
        self.up()


# -- RotationalGuidance --

global_null_angle = 0

def bias(yaw_angle, null_angle=global_null_angle):
    print("null_angle: " + str(null_angle))
    if null_angle == 0:
        print("null_angle ====== 0")
        return yaw_angle
    new_angle = yaw_angle - null_angle
    if new_angle == 180:
        return -180
    if new_angle > 180:
        return -(180 - (new_angle - 180))
    if new_angle < -180:
        return -180 + (new_angle + 180)
    return new_angle

def get_bias(null_angle=global_null_angle):
    null_angle = global_null_angle
    angle = hub.motion_sensor.get_yaw_angle()
    return angle ##
    new_angle = bias(angle, null_angle=null_angle)
    print("angle: " + str(angle) + "null angle: " + str(null_angle) + "new_angle: " + str(new_angle))
    return new_angle


class RotationalGuidance:

    def left(self, degrees, speed=40, dgr_offset=6):
        hub.motion_sensor.reset_yaw_angle() ##
        null_angle = hub.motion_sensor.get_yaw_angle()
        while True:
            motors.start_tank(-speed, speed)
            angle = get_bias(null_angle=null_angle)
            print(str(angle))
            if angle <= -(degrees-dgr_offset) or angle > 0:
                motors.stop()
                print("---------------------------------------------")
                return

    def right(self, degrees, speed=40, dgr_offset=6):
        hub.motion_sensor.reset_yaw_angle() ##
        null_angle = hub.motion_sensor.get_yaw_angle()
        while True:
            motors.start_tank(speed, -speed)
            angle = get_bias(null_angle=null_angle)
            #print(str(angle))
            if angle >= (degrees-dgr_offset) or angle < 0:
                print("---------------------------------------------")
                motors.stop()
                return

    def drive_straight(self, seconds, speed=40, reset_yaw_angle=True):
        print(seconds)
        #if reset_yaw_angle:
        hub.motion_sensor.reset_yaw_angle() ##
        null_angle = hub.motion_sensor.get_yaw_angle()
        start_time = time.time()
        while True:
            time_passed = time.time() - start_time
            if time_passed >= float(seconds):
                motors.stop()
                return

            steering = int(get_bias(null_angle=null_angle) * 5)
            motors.start(steering=-steering, speed=speed)

rotate = RotationalGuidance()

activate_arm = True
if activate_arm:
    arm = ArmControl()
    arm.calibrate()

activate_guidance = True
if activate_guidance:
    guidance = LineGuidance()
    guidance.initialize()

# wait for start

#hub.right_button.wait_until_pressed()
while True:
    if hub.motion_sensor.get_pitch_angle() < -7:
        break

hub.speaker.beep(80, 0.7)

#$content$
