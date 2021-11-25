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
    
    def run(self):
        self.crossings_left = -1
        for instruction in self.instructions:
            self.execute_instruction(instruction)
    
    light_pr = light_b
    light_sc = light_a
    invert_steering = True
    
    crossings_left = -1
    is_crossing = False

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

                #rgb = self.light_sc.get_rgb_intensity()
                #sc_on_track = (fabs(rgb[0] - rgb[1]) < rgb_margin) and (fabs(rgb[1] - rgb [2]) < rgb_margin) and (fabs(rgb[0] - rgb[2]) < rgb_margin)
                #sc_on_track = sc_on_track and ( light_sc_percent > 0.9 or light_sc_percent < 0.1 )
                #if sc_on_track: 
                #    if sc_on_track_start == -1:
                #        sc_on_track_start = time.time
                #    else:
                #        sc_on_track = sc_on_track and time.time - sc_on_track_start > 0.3
                #else:
                #    sc_on_track_start = -1
                #print(str(fabs(rgb[0] - rgb[1])) + " " + str(fabs(rgb[1] - rgb[2])) + " " + str(fabs(rgb[0] - rgb[2])))
                #if sc_on_track:
                #    hub.status_light.on("green")
                #else:
                #    hub.status_light.on("blue")
                is_crossing = self.light_sc.get_color() == "black"
                if is_crossing:
                    hub.status_light.on("green")
                else:
                    hub.status_light.on("blue")
                if self.is_crossing != is_crossing:
                    if is_crossing:
                        motors.stop()
                        hub.speaker.start_beep(60)
                        self.crossings_left = self.crossings_left - 1
                        if self.crossings_left == 0:

                            hub.speaker.beep(80, 1)

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
                    else:
                        hub.speaker.stop()

                    self.is_crossing = is_crossing

                steering = (light_pr_percent - 0.5) * 100
                dynamic_speed = speed - ( abs(steering)/100 * (speed - maneuvering_speed) )
                if self.invert_steering: steering = -steering
                motors.start_at_power(int(dynamic_speed), int(steering))

        # ----- drive and take crossing -----
        if instruction_name == "drive_and_take_crossing" and length == 2:
            self.crossings_left = int(instruction[1])
            print("driving and taking crossing " + str(self.crossings_left) + "...")
            self.execute_instruction(("drive",))

guidance = LineGuidance()
guidance.initialize()

# wait for start
hub.right_button.wait_until_pressed()
hub.speaker.beep(80, 0.7)

motors.move(10)

# programming space

#guidance.drive()
guidance.drive_and_take_crossing(1)
guidance.run()
