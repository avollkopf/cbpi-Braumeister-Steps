# Plugin for usage of Craftbeerpi3 with the Speidel Braumeister
***Update (30.12.2020)
- Added button to mash- and boilstep that allows to add 5 minutes to the step (can be pressed several times)
	- Can be used in case gravity is not where it should be and mash step should be extended

## Hardware requirements 
- (Tested with a) Speidel Braumeister 20 Plus (2015).
- Should also work with the 10  and 50 Liter models. However, for the 50 Liter model you need to figure out on how to manage the two pumps and heaters.
- I recommend to use the original temp sensor from the Braumeister which is a 2 wire PT1000. In this case you don't need to deal with thermowells that may not fir into the existing hole of the Braumeister.
	- Therefore you need to add a max31865 board (incl. a 4300 ohm resistor for PT1000) to your craftbeerpi hardware setup. (https://learn.adafruit.com/adafruit-max31865-rtd-pt100-amplifier/)
	- To connect to the probe, you need a Binder coupling connector (https://www.conrad.de/de/p/binder-99-0406-00-03-rundstecker-kupplung-gerade-serie-rundsteckverbinder-712-gesamtpolzahl-3-1-st-738917.html)
	- You just need to unplug the probe from the Braumeister controller and plug your cable with the aforementioned connector to your craftbeerpi setup
- To connect the pump and the heater, you will need hirschmann connectors. I am using the following connectors
	- Hirschmann STAK 2 for the pump (https://www.conrad.de/de/p/hirschmann-stak-2-netz-steckverbinder-stak-serie-netzsteckverbinder-stak-buchse-gerade-gesamtpolzahl-2-pe-16-a-gra-1177484.html)
	- Hirschmann STAK 200 for the heating element (https://www.conrad.de/de/p/hirschmann-stak-200-netz-steckverbinder-stak-serie-netzsteckverbinder-stak-buchse-gerade-gesamtpolzahl-2-pe-16-a-g-730025.html)
	- You will need 2 Hirschmann safety Clips (https://www.conrad.de/de/p/sicherungsbuegel-hirschmann-730980.html)
	- Just unplug pump and heater and connect it to your Relais outputs. I am using SSR for both, heater and pump. They can handle 20A @ 240V AC
- Thats about it for the hardware part.

## Software requirements (READ FIRST)
- You need an installation of craftbeerpi3 with some additional plugins.
- I have already modified the beerxml and Kleiner Brauhelfer recipe plugin on my forked craftbeerpi3 repo to handle recipe import for the Braumeister
- You can download it here: https://github.com/avollkopf/craftbeerpi3
- You will need the PT100X plugin to read the temeprature values from the PT1000 and configure it to PT1000.
- You can download it here: https://github.com/avollkopf/cbpi-pt100-sensor
	- This is a fork from the PT100 plugin (https://github.com/thegreathoe/cbpi-pt100-sensor) where I just added PT1000 support
- And you will need the cbpi Braumeister steps plugin which you can find here: https://github.com/avollkopf/cbpi-Braumeister-Steps
	- This plugin adds a parameter bm_recipe_creation to the Craftbeerpi3 Paramaters.
	- If you import a beerxml file or a recipe from the Kleiner Brauhelfer 2 application and want craftbeerpi to create steps for the Braumeister, you need to set this parameter to 'YES'
	- The plugin contains a slighlty modified version of the PIDSmartBoilwithPump (https://github.com/cgspeck/cbpi-pidsmartboil-withpump)
	- It's called BM_PIDSmartBoilWithPump and you need to select this as logic for your Braumeister as it switches off your pump at 88°C (not yet tested for F)
	- PID settings have to be optimized for your kettle with the PIDAutotune plugin
	- PID control switches off at 88°C and boiling will be done with reduced heater power which can be defined as in the original plugin (default is 70%)
- I do recommend to install and use also the Pushover Plugin to recieve push notifications when you need to add or remove the malt pipe or add hops.
- The BM_... steps switch auto mode on and off automatically (e.g. to add or remove the malt pipe) This functionionality has been copied from the cbpi-SimpleUtilitySteps (https://github.com/MiracelVip/cbpi-SimpleUtilitySteps)
	
## Step creation from a beer.xml file or Kleiner Brauhelfer 2 databse file
- For beer.xml recipes upload a beerxml file (e.g. from Beersmith - tested on my side)
- For Kleiner Brauhelfer 2, upload the databse to craftbeerpi
- Import the recipe to craftbeerpi with (bm_recipe_creation must be set to YES)
- The software now adds a mashin step that switches to automode once you start the process flow.
	- Once mashin temperature is reached, it switches off Auto mode and asks you to add the malt pipe and malt.
	- This step asks you to press the next button to move to the next step. Be carefull, as the auto mode starts again and Pump/Heater is switching bakc on
- The next steps that will be automatically created are the mash steps (can be more then one depending on your recipe)
- After the mash out step is completed, the recipe import adds a step that reminds you to remove the malt pipe and to sparge. 
	- This step also stops the auto mode (pump and heater)
	- The next step is triggered once you click next step.
- If the recipe has first wort hops, the import adds a first wort step that reminds you to add hops at this point. No waiting implemented to start boiling.
- The boiling step is also added automatically and starts right after first wort hops if included in the recipe.Otherwise it starts right after removal of the malt pipe and confirmation.
- Hop and misc alarms are automatically added.
- last step that is automatically addad is the Whirlpool for 15 minutes.

