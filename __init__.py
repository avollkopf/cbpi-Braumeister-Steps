# -*- coding: utf-8 -*-
################################################################################
import logging

from modules.core.controller import KettleController
from modules.core.props import Property, StepProperty
from modules.core.step import StepBase
from modules import cbpi
import time
from os import system, listdir, remove

LOG_DIR = "./logs/"
APP_LOG = "app.log"
LOG_SEP = "-=-"


def BM_RecipeCreation():
	global bm_recipe_creation
	bm_recipe_creation = cbpi.get_config_parameter("bm_recipe_creation", None)
	if bm_recipe_creation is None:
		print ("INIT BM Recipe Creation Flag")
		try:
                    cbpi.add_config_parameter("bm_recipe_creation", "NO", "select", "Braumeister Recipe Creation Flag", ["YES", "NO"])
                    bm_recipe_creation = cbpi.get_config_parameter("bm_recipe_creation", None)
		except:
                    cbpi.notify("Braumeister Error", "Unable to update database. Update CraftBeerPi and reboot.", type="danger", timeout=None)

@cbpi.initalizer(order=9000)
def init(cbpi):
        global BM_Recipes
        cbpi.app.logger.info("INITIALIZE  Braumeister Recipe PLUGIN")
        BM_RecipeCreation()
        if  bm_recipe_creation is None or not bm_recipe_creation:
            cbpi.notify("Braumeister Recipe  Error", "Check Braumeister Recipe Flag is set", type="danger", timeout=None)
        else:
            BM_Recipes = "OK"


##################################################################################
@cbpi.step
class BM_MashInStep(StepBase):
    '''
    Just put the decorator @cbpi.step on top of a method
    '''
    # Properties
    temp = Property.Number("Temperature", configurable=True,  description="Target Temperature of Mash Step")
    kettle = StepProperty.Kettle("Kettle", description="Kettle in which the mashing takes place")
    s = False

    @cbpi.action("Change Power")
    def change_power(self):
        self.actor_power(1, 50)

    def init(self):
        '''
        Initialize Step. This method is called once at the beginning of the step
        :return:
        '''
        # set target tep
        self.s = False
        self.set_target_temp(self.temp, self.kettle)
        self.setAutoMode(True)


    def execute(self):
        '''
        This method is execute in an interval
        :return:
        '''

        # Check if Target Temp is reached
        if self.get_kettle_temp(self.kettle) >= float(self.temp) and self.s is False:
            self.s = True
            self.setAutoMode(False)
            self.notify("MashIn Step Temp Reached!", "Please add Malt Pipe and malt. Press next to continue", timeout=None)
    #-------------------------------------------------------------------------------
    def setAutoMode(self, auto_state):
        try:
            kettle = cbpi.cache.get("kettle")[int(self.kettle)]
            if (kettle.state is False) and (auto_state is True):
                # turn on
                if kettle.logic is not None:
                    cfg = kettle.config.copy()
                    cfg.update(dict(api=cbpi, kettle_id=kettle.id, heater=kettle.heater, sensor=kettle.sensor))
                    instance = cbpi.get_controller(kettle.logic).get("class")(**cfg)
                    instance.init()
                    kettle.instance = instance
                    def run(instance):
                        instance.run()
                    t = cbpi.socketio.start_background_task(target=run, instance=instance)
                kettle.state = not kettle.state
                cbpi.emit("UPDATE_KETTLE", cbpi.cache.get("kettle")[int(self.kettle)])
            elif (kettle.state is True) and (auto_state is False):
                # turn off
                kettle.instance.stop()
                kettle.state = not kettle.state
                cbpi.emit("UPDATE_KETTLE", cbpi.cache.get("kettle")[int(self.kettle)])
        except Exception as e:
            cbpi.notify("Error", "Failed to set Auto mode {}".format(["OFF","ON"][auto_state]), type="danger", timeout=None)
            cbpi.app.logger.error(e)

################################################################################
@cbpi.step
class BM_ManualStep(StepBase):
    # Properties
    heading = Property.Text("Heading", configurable=True, default_value="Step Alert", description="First line of notification.")
    message = Property.Text("Message", configurable=True, default_value="Press next button to continue", description="Second line of notification.")
    notifyType = Property.Select("Type", options=["success","info","warning","danger"])
    proceed = Property.Select("Next Step", options=["Pause","Continue"], description="Whether or not to automatically continue to the next brew step.")
    s = False
    #-------------------------------------------------------------------------------

    @cbpi.action("Start Timer Now")
    def init(self):
        if self.notifyType not in ["success","info","warning","danger"]:
            self.notifyType = "info"

    def execute(self):
        '''
        This method is execute in an interval
        :return:
        '''

        # Check if Target Temp is reached
        if self.s is False:
            self.s = True
            self.notify(self.heading, self.message, type=self.notifyType, timeout=None)
            if self.proceed == "Continue":
                #Python 2
                try: 
                    self.next()
                #Python3
                except:
                    next(self)
                pass

################################################################################
@cbpi.step
class BM_MashStep(StepBase):
    '''
    Just put the decorator @cbpi.step on top of a method
    '''
    # Properties
    temp = Property.Number("Temperature", configurable=True, description="Target Temperature of Mash Step")
    kettle = StepProperty.Kettle("Kettle", description="Kettle in which the mashing takes place")
    timer = Property.Number("Timer in Minutes", configurable=True, description="Timer is started when the target temperature is reached")

    def init(self):
        '''
        Initialize Step. This method is called once at the beginning of the step
        :return:
        '''
        # set target tep
        self.set_target_temp(self.temp, self.kettle)
        self.setAutoMode(True)

    @cbpi.action("Start Timer Now")
    def start(self):
        '''
        Custom Action which can be execute form the brewing dashboard.
        All method with decorator @cbpi.action("YOUR CUSTOM NAME") will be available in the user interface
        :return:
        '''
        if self.is_timer_finished() is None:
            self.start_timer(int(self.timer) * 60)

    def reset(self):
        self.stop_timer()
        self.set_target_temp(self.temp, self.kettle)

    def finish(self):
        self.set_target_temp(0, self.kettle)

    def execute(self):

        '''
        This method is execute in an interval
        :return:
        '''

        # Check if Target Temp is reached
        if self.get_kettle_temp(self.kettle) >= float(self.temp):
            # Check if Timer is Running
            if self.is_timer_finished() is None:
                self.start_timer(int(self.timer) * 60)

        # Check if timer finished and go to next step
        if self.is_timer_finished() == True:
            self.setAutoMode(False)
            self.notify("Mash Step %s Completed!" % self.name, "Starting the next step", timeout=None)
            #Python 2
            try: 
                self.next()
            #Python3
            except:
                next(self)
            pass

    #-------------------------------------------------------------------------------
    def setAutoMode(self, auto_state):
        try:
            kettle = cbpi.cache.get("kettle")[int(self.kettle)]
            if (kettle.state is False) and (auto_state is True):
                # turn on
                if kettle.logic is not None:
                    cfg = kettle.config.copy()
                    cfg.update(dict(api=cbpi, kettle_id=kettle.id, heater=kettle.heater, sensor=kettle.sensor))
                    instance = cbpi.get_controller(kettle.logic).get("class")(**cfg)
                    instance.init()
                    kettle.instance = instance
                    def run(instance):
                        instance.run()
                    t = cbpi.socketio.start_background_task(target=run, instance=instance)
                kettle.state = not kettle.state
                cbpi.emit("UPDATE_KETTLE", cbpi.cache.get("kettle")[int(self.kettle)])
            elif (kettle.state is True) and (auto_state is False):
                # turn off
                kettle.instance.stop()
                kettle.state = not kettle.state
                cbpi.emit("UPDATE_KETTLE", cbpi.cache.get("kettle")[int(self.kettle)])
        except Exception as e:
            cbpi.notify("Error", "Failed to set Auto mode {}".format(["OFF","ON"][auto_state]), type="danger", timeout=None)
            cbpi.app.logger.error(e)

##############################################################################        
@cbpi.step
class BM_BoilStep(StepBase):
    '''
    Just put the decorator @cbpi.step on top of a method
    '''
    # Properties
    lid_temp = 95 # temp in C for lid removal alarm during boil
    lid_flag = False
    first_wort_hop_flag = False
    temp = Property.Number("Temperature", configurable=True, default_value=100, description="Target temperature for boiling")
    kettle = StepProperty.Kettle("Kettle", description="Kettle in which the boiling step takes place")
    timer = Property.Number("Timer in Minutes", configurable=True, description="Timer is started when target temperature is reached")
    first_wort_hop = Property.Select("First Wort Hop Addition", options=["Yes","No"], description="First Wort Hop alert if set to Yes")
    hop_1 = Property.Number("Hop 1 Addition", configurable=True, description="First Hop alert (minutes before finish)")
    hop_1_added = Property.Number("",default_value=None)
    hop_2 = Property.Number("Hop 2 Addition", configurable=True, description="Second Hop alert (minutes before finish)")
    hop_2_added = Property.Number("", default_value=None)
    hop_3 = Property.Number("Hop 3 Addition", configurable=True, description="Third Hop alert (minutes before finish)")
    hop_3_added = Property.Number("", default_value=None)
    hop_4 = Property.Number("Hop 4 Addition", configurable=True, description="Fourth Hop alert (minutes before finish)")
    hop_4_added = Property.Number("", default_value=None)
    hop_5 = Property.Number("Hop 5 Addition", configurable=True, description="Fifth Hop alert (minutes before finish)")
    hop_5_added = Property.Number("", default_value=None)

    def init(self):
        '''
        Initialize Step. This method is called once at the beginning of the step
        :return:
        '''
        # set target tep
        self.set_target_temp(self.temp, self.kettle)
        self.setAutoMode(True)
        # if temp unit is F, calculate set temnp from C to F
        if cbpi.get_config_parameter("unit", "C") != "C": 
            self.lid_temp = round(9.0 / 5.0 * self.lid_temp + 32, 2)

    @cbpi.action("Start Timer Now")
    def start(self):
        '''
        Custom Action which can be execute form the brewing dashboard.
        All method with decorator @cbpi.action("YOUR CUSTOM NAME") will be available in the user interface
        :return:
        '''
        if self.is_timer_finished() is None:
            self.start_timer(int(self.timer) * 60)

    def reset(self):
        self.stop_timer()
        self.set_target_temp(self.temp, self.kettle)

    def finish(self):
        self.set_target_temp(0, self.kettle)
        self.setAutoMode(False)


    def check_hop_timer(self, number, value):
        s = cbpi.cache.get("active_step")
        hop_added = getattr(s,"hop_%s_added" % number)
        if value is not None and hop_added is not True:
            if time.time() > (self.timer_end - int(value) * 60):
                self.__setattr__("hop_%s_added" % number, True)
                self.notify("Hop Alert", "Please add Hop %s" % number, timeout=None)

    def execute(self):
        '''
        This method is execute in an interval
        :return:
        '''
        if self.first_wort_hop_flag == False and self.first_wort_hop == "Yes":
            self.first_wort_hop_flag = True
            self.notify("First Wort Hop Addition!","Please add hops for first wort",timeout=None)

        if self.lid_flag == False and self.get_kettle_temp(self.kettle) >= self.lid_temp:
            self.notify("Please remove lid!", "Reached temp close to boiling", timeout=None)
            self.lid_flag = True

        '''
        This method is execute in an interval
        :return:
        '''
        # Check if Target Temp is reached
        if self.get_kettle_temp(self.kettle) >= float(self.temp):
            # Check if Timer is Running
            if self.is_timer_finished() is None:
                self.start_timer(int(self.timer) * 60)
            else:
                self.check_hop_timer(1, self.hop_1)
                self.check_hop_timer(2, self.hop_2)
                self.check_hop_timer(3, self.hop_3)
                self.check_hop_timer(4, self.hop_4)
                self.check_hop_timer(5, self.hop_5)

        # Check if timer finished and go to next step
        if self.is_timer_finished() == True:
            self.setAutoMode(False)
            self.notify("Boil Step Completed!", "Starting the next step", timeout=None)
            #Python 2
            try: 
                self.next()
            #Python3
            except:
                next(self)
            pass

    #-------------------------------------------------------------------------------
    def setAutoMode(self, auto_state):
        try:
            kettle = cbpi.cache.get("kettle")[int(self.kettle)]
            if (kettle.state is False) and (auto_state is True):
                # turn on
                if kettle.logic is not None:
                    cfg = kettle.config.copy()
                    cfg.update(dict(api=cbpi, kettle_id=kettle.id, heater=kettle.heater, sensor=kettle.sensor))
                    instance = cbpi.get_controller(kettle.logic).get("class")(**cfg)
                    instance.init()
                    kettle.instance = instance
                    def run(instance):
                        instance.run()
                    t = cbpi.socketio.start_background_task(target=run, instance=instance)
                kettle.state = not kettle.state
                cbpi.emit("UPDATE_KETTLE", cbpi.cache.get("kettle")[int(self.kettle)])
            elif (kettle.state is True) and (auto_state is False):
                # turn off
                kettle.instance.stop()
                kettle.state = not kettle.state
                cbpi.emit("UPDATE_KETTLE", cbpi.cache.get("kettle")[int(self.kettle)])
        except Exception as e:
            cbpi.notify("Error", "Failed to set Auto mode {}".format(["OFF","ON"][auto_state]), type="danger", timeout=None)
            cbpi.app.logger.error(e)

#######################################################################################

#######################################################################################

@cbpi.controller
class BM_PIDSmartBoilWithPump(KettleController):

    a_p = Property.Number("P", True, 117.0795, description="P Value of PID")
    b_i = Property.Number("I", True, 0.2747, description="I Value of PID")
    c_d = Property.Number("D", True, 41.58, description="D Value of PID")
    d_max_output = Property.Number("Max Output %", True, 100, description="Max power for PID and Ramp up.")
    e_max_temp_pid = Property.Number("Max PID Target Temperature", False, 88,description="If Target Temperature (C) is set above this, PID will be disabled and Boil Mode will turn on.")        
    f_max_output_boil = Property.Number("Max Boil Output %", True, 85, description="Power when Max Boil Temperature is reached.")
    g_max_temp_boil = Property.Number("Max Boil Temperature", True, 98,description="When Temperature reaches this, power will be reduced to Max Boil Output.")

    h_internal_loop_time = Property.Number("Internal loop time", True, 0.2, description="In seconds, how quickly the internal loop will run, dictates maximum PID resolution.")

    i_mash_pump_rest_interval = Property.Number("Mash pump rest interval", True, 600, description="Rest the pump after this many seconds during the mash.")

    j_mash_pump_rest_time = Property.Number("Mash pump rest time", True, 60, description="Rest the pump for this many seconds every rest interval.")

    k_pump_max_temp = Property.Number("Pump maximum temperature", False, 88, description="The pump will be switched off after the boil reaches this temperature (C).")


    def __init__(self, *args, **kwds):
        KettleController.__init__(self, *args, **kwds)
        self._logger = logging.getLogger(type(self).__name__)


    @cbpi.try_catch(None)
    def agitator_on(self):
        k = self.api.cache.get("kettle").get(self.kettle_id)
        if k.agitator is not None:
            self.actor_on(power=100, id=int(k.agitator))


    @cbpi.try_catch(None)
    def agitator_off(self):
        k = self.api.cache.get("kettle").get(self.kettle_id)
        if k.agitator is not None:
            self.actor_off(int(k.agitator))


    def stop(self):
        '''
        Invoked when the automatic is stopped.
        Normally you switch off the actors and clean up everything
        :return: None
        '''
        super(KettleController, self).stop()
        self.heater_off()
        self.agitator_off()

    def run(self):
        wait_time = sampleTime = 5
        p = float(self.a_p)
        i = float(self.b_i)
        d = float(self.c_d)
        
        maxoutput = float(self.d_max_output)
        # convert value to if, if F is set in cofig
        if cbpi.get_config_parameter("unit", "C") != "C":        
            maxtemppid = round(9.0 / 5.0 * self.e_max_temp_pid + 32, 2)
        else:
            maxtemppid = float(self.e_max_temp_pid)
        
        pid = BM_PIDArduino(sampleTime, p, i, d, 0, maxoutput)
        
        maxoutputboil = float(self.f_max_output_boil)
        maxtempboil = float(self.g_max_temp_boil)

        if maxtempboil > maxoutput:
            raise ValueError('maxtempboil must be less than maxoutput') # does this makes sense to compare temp with power %?

        self.start_time = time.time()
        internal_loop_time = float(self.h_internal_loop_time)
        self._logger.debug(self.h_internal_loop_time)
        self._logger.debug(internal_loop_time)

        mash_pump_rest_interval = int(self.i_mash_pump_rest_interval)
        mash_pump_rest_time = int(self.j_mash_pump_rest_time)

        next_pump_start = 0
        next_pump_rest = None

        # convert value to if, if F is set in cofig
        if cbpi.get_config_parameter("unit", "C") != "C":        
            pump_max_temp = round(9.0 / 5.0 * self.k_pump_max_temp + 32, 2)
        else:       
            pump_max_temp = int(self.k_pump_max_temp)
        pump_boil_auto_off_control_enabled = True

        while self.is_running():
            self._logger.debug("calculation cycle")
            inner_loop_now = calculation_loop_start = time.time()
            next_calculation_time = calculation_loop_start + sampleTime
            target_temp = self.get_target_temp()
            current_temp = self.get_temp()
            boil_mode = current_temp > maxtemppid # changed from target_temp according to descriptio above maxtempPID should be smaller than pump_max_temp

            if not boil_mode: #PID
                heat_percent = pid.calc(current_temp, target_temp)
            elif current_temp < maxtempboil: #Boil Ramp
                heat_percent = maxoutput
            else: #Boil Sustain
                heat_percent = maxoutputboil
                
            heating_time = sampleTime * heat_percent / 100
            heat_to = calculation_loop_start + heating_time

            wait_time = sampleTime - heating_time

            while inner_loop_now < next_calculation_time:
                self._logger.debug("inner loop cycle")

                if inner_loop_now == calculation_loop_start and heating_time > 0:
                    self._logger.debug("inner loop heat on")
                    self.heater_on(100)

                if inner_loop_now > calculation_loop_start and \
                        inner_loop_now >= heat_to and \
                        wait_time > 0:
                    self._logger.debug("inner loop heat off")
                    self.heater_off()
                    wait_time = -1  # to stop off being called continuously

                if boil_mode:
                    if current_temp > pump_max_temp and pump_boil_auto_off_control_enabled:
                        self._logger.debug("pump off and auto off disabled")
                        pump_boil_auto_off_control_enabled = False
                        self._logger.debug("further mash pump logic is disabled") 
                        next_pump_start = None
                        next_pump_rest = None
                        self.agitator_off()
                    else:
                        self._logger.debug("pump restarted and auto off enabled")
                        pump_boil_auto_off_control_enabled = True
                        self.agitator_off()
                else:
                    if next_pump_start is not None and inner_loop_now >= next_pump_start:
                        self._logger.debug("starting pump")
                        next_pump_start = None
                        next_pump_rest = inner_loop_now + mash_pump_rest_interval
                        self.agitator_on()
                    elif next_pump_rest is not None and inner_loop_now >= next_pump_rest:
                        self._logger.debug("resting pump")
                        next_pump_rest = None
                        next_pump_start = inner_loop_now + mash_pump_rest_time
                        self.agitator_off()

                self.sleep(internal_loop_time)
                inner_loop_now = time.time()

# Based on Arduino PID Library
# See https://github.com/br3ttb/Arduino-PID-Library
class BM_PIDArduino(object):

    def __init__(self, sampleTimeSec, kp, ki, kd, outputMin=float('-inf'),
                 outputMax=float('inf'), getTimeMs=None):
        if kp is None:
            raise ValueError('kp must be specified')
        if ki is None:
            raise ValueError('ki must be specified')
        if kd is None:
            raise ValueError('kd must be specified')
        if float(sampleTimeSec) <= float(0):
            raise ValueError('sampleTimeSec must be greater than 0')
        if outputMin >= outputMax:
            raise ValueError('outputMin must be less than outputMax')

        self._logger = logging.getLogger(type(self).__name__)
        self._Kp = kp
        self._Ki = ki * sampleTimeSec
        self._Kd = kd / sampleTimeSec
        self._sampleTime = sampleTimeSec * 1000
        self._outputMin = outputMin
        self._outputMax = outputMax
        self._iTerm = 0
        self._lastInput = 0
        self._lastOutput = 0
        self._lastCalc = 0

        if getTimeMs is None:
            self._getTimeMs = self._currentTimeMs
        else:
            self._getTimeMs = getTimeMs

    def calc(self, inputValue, setpoint):
        now = self._getTimeMs()

        if (now - self._lastCalc) < self._sampleTime:
            return self._lastOutput

        # Compute all the working error variables
        error = setpoint - inputValue
        dInput = inputValue - self._lastInput

        # In order to prevent windup, only integrate if the process is not saturated
        if self._lastOutput < self._outputMax and self._lastOutput > self._outputMin:
            self._iTerm += self._Ki * error
            self._iTerm = min(self._iTerm, self._outputMax)
            self._iTerm = max(self._iTerm, self._outputMin)

        p = self._Kp * error
        i = self._iTerm
        d = -(self._Kd * dInput)

        # Compute PID Output
        self._lastOutput = p + i + d
        self._lastOutput = min(self._lastOutput, self._outputMax)
        self._lastOutput = max(self._lastOutput, self._outputMin)

        # Log some debug info
        self._logger.debug('P: {0}'.format(p))
        self._logger.debug('I: {0}'.format(i))
        self._logger.debug('D: {0}'.format(d))
        self._logger.debug('output: {0}'.format(self._lastOutput))

        # Remember some variables for next time
        self._lastInput = inputValue
        self._lastCalc = now
        return self._lastOutput

    def _currentTimeMs(self):
        return time.time() * 1000
