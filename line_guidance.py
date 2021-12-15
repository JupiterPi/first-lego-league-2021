from spike import PrimeHub, LightMatrix, Button, StatusLight, ForceSensor, MotionSensor, Speaker, ColorSensor, App, DistanceSensor, Motor, MotorPair
from spike.control import wait_for_seconds, wait_until, Timer
from math import *
import time

# establish port connections
hub = PrimeHub()
motors = MotorPair('C', 'D')
light_a = ColorSensor('A')
light_b = ColorSensor('B')

# speed configuration
speed = 60
maneuvering_speed = 50
high_maneuvering_speed = 20

# other configuration
rgb_margin = 0.05 * 1024 # (how much rgb values may differ in order for it to be interpreted as grayscale)

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
        print("drive")
        self.instructions.append(("drive",))

    def drive_and_take_crossing(self, crossing_target):
        print("drive and take crossing " + str(crossing_target))
        self.instructions.append(("drive_and_take_crossing", str(crossing_target)))

    def drive_to_crossing(self, crossing_target):
        print("drive to crossing " + str(crossing_target))
        self.instructions.append(("drive_to_crossing", str(crossing_target)))

    def switch_to_lane(self, new_lane): # new_lane = 'A' or 'B'
        print("switching to lane " + new_lane)
        self.instructions.append(("switch_to_lane", new_lane))
    
    def manually_switch_to_lane(self, new_lane): # new_lane = 'A' or 'B'
        print("manually switching to lane " + new_lane)
        self.instructions.append(("manually_switch_to_lane", new_lane))

    def drive_for(self, seconds):
        print("driving for (s) " + str(seconds))
        self.instructions.append(("drive_for", seconds))

    def run(self):
        self.crossings_left = -1
        for instruction in self.instructions:
            self.execute_instruction(instruction)

    light_pr = light_b
    light_sc = light_a
    invert_steering = True

    crossings_left = -1
    lastly_crossing = False
    crossing_do_turn = False

    start_time = -1
    time_target = -1

    sc_on_track_start = -1

    def execute_instruction(self, instruction):
        print("executing instruction: " + str(instruction))

        # ----- drive -----
        instruction_name = instruction[0]
        print("instruction name: " + str(instruction_name))
        length = len(instruction)
        print("length: " + str(length))
        if instruction_name == "drive" and length == 1:
            print("driving...")
            while True:

                light_pr_percent = (self.light_pr.get_reflected_light() - self.min_light) / (self.max_light - self.min_light)
                light_sc_percent = (self.light_sc.get_reflected_light() - self.min_light) / (self.max_light - self.min_light)

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


        # ----- drive and take crossing -----
        if instruction_name == "drive_and_take_crossing" and length == 2:
            self.crossings_left = int(instruction[1])
            self.crossing_do_turn = True
            print("driving and taking crossing " + str(self.crossings_left) + "...")
            self.execute_instruction(("drive",))

        # ----- drive to crossing -----
        if instruction_name == "drive_to_crossing" and length == 2:
            self.crossings_left = int(instruction[1])
            self.crossing_do_turn = False
            print("driving to crossing " + str(self.crossings_left) + "...")
            self.execute_instruction(("drive",))

        # ----- drive for -----
        if instruction_name == "drive_for" and length == 2:
            self.time_target = int(instruction[1])
            self.execute_instruction(("drive",))

        # ----- switch to lane -----
        if instruction_name == "switch_to_lane" and length == 2:
            new_lane = instruction[1]
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
            print("start time: " + str(start_time))
            while True:
                if new_lane == "A":
                    print("A...")
                    motors.start_tank_at_power(maneuvering_speed, int(maneuvering_speed * 0.05))
                else:
                    print("B...")
                    motors.start_tank_at_power(int(maneuvering_speed * 0.05), maneuvering_speed)
                if self.light_pr.get_color() == "black":
                    print("saw black")
                    motors.stop()
                    break
            print("current time: " + str(time.time()))
            print("start time: " + str(start_time))
            duration = time.time() - start_time
            duration = 1    #######################
            print("duration: " + str(duration))
            new_time = duration * 0.8
            print("new time: " + str(new_time))
            start_time = time.time()
            print("start time: " + str(start_time))
            if new_lane == "B":
                print("B...")
                motors.move_tank(new_time, unit="seconds", left_speed=maneuvering_speed, right_speed=int(maneuvering_speed * 0.05))
            else:
                print("A...")
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
            print("realigned")

        # ----- manually switch to lane -----
        if instruction_name == "manually_switch_to_lane" and length == 2:
            new_lane = instruction[1]
            print("manually switching to lane: " + new_lane)
            print("is A")
            self.light_pr = light_a
            self.light_sc = light_b
            self.invert_steering = False
            if new_lane == "B":
                print("is B")
                self.light_pr = light_b
                self.light_sc = light_a
                self.invert_steering = True

guidance = LineGuidance()
guidance.initialize()

# wait for start
hub.right_button.wait_until_pressed()
hub.speaker.beep(80, 0.7)

motors.move(10)

# programming space

guidance.drive_to_crossing(4)
guidance.run()

motors.move_tank(1, "seconds", left_speed=50, right_speed=50)
motors.move_tank(1, "seconds", left_speed=-30, right_speed=-30)
motors.move_tank(1, "seconds", left_speed=50, right_speed=0)
motors.move_tank(1, "seconds", left_speed=-10, right_speed=-10)

guidance.manually_switch_to_lane("A")

time.sleep(1)

guidance.drive()
guidance.run()
