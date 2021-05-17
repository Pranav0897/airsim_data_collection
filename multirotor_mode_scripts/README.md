### Overview
This code extends the data collection scripts provided by the Airsim team in [this repo](https://github.com/Microsoft/DroneRescue), by using Unreal's Python API to get locations of objects-of-interest and orbiting the drone around them and collecting data, in Multi-rotor mode.

First, to utilize multirotor mode, you can use the settings.json file in this folder, or your own settings.json file, and move it to your Airsim directory (typically `C:/Users/<username>/Documents/Airsim` on Windows)

#### This readme servers as a compilation of notes and instructions to use the code in this repo
Unreal extends its functionality by providing API calls in Python. However, there's a major caveat to this: you can only work with the blueprint before a game is running; as far as I can tell, you can't make the game play or pause from the python script, nor access actor locations when the game is running.

So, to get the actor locations, we create a python script which utilizes unreal's API to get actor locations before we start the game. We can do this two ways:
- **Method 1:** Add the script as a startup script to the project. That way, when you open up the project in Unreal Editor, this script runs in the background, and stores the locations of the barrel, and the starting point in a file which the airsim script can then access when running later. To do this:
Select `Edit > Project Settings....` Under the `Plugins` list, select `Python`. Then, add your scripts to the `Startup scripts` setting (see the figure in [Unreal's intro to Scripting](https://docs.unrealengine.com/en-US/ProductionPipelines/ScriptingAndAutomation/Python/#startupscripts)
Restart the Unreal Editor when done. The next time the Editor loads your Project, it should run your new startup scripts. You can do this for all the projects you want to work with.
- **Method 2:** Open up project in Unreal Editor manually, and open the Python console in the Output Log (see [Unreal's intro to scripting](https://docs.unrealengine.com/en-US/ProductionPipelines/ScriptingAndAutomation/Python/#thepythonconsoleintheoutputlog)), and call your script. This method is useful if you want to programmatically move your objects in the scene; all you need to do is find the relevant Actor in the scene, and set it's location to your desired value. Beware of the main caveat with the Unreal scripting: the python script seems unable to get the actor information, or modify it while a game is running, so you can't move the object-of-interest mid-simulation.

Before you start the game, make sure you have exactly one PlayerStart Actor in the scene (it currently doesn't work with more than one PlayerStart actors in the scene; to add this functionality, we need to find a way to decide which of the PlayerStart actors the player is going to use to spawn when the game starts. Once we figure that out, we can specify the start location as the location of this PlayerStart actor). To add a Player Start actor, go to `Window > Place Actors....` Under the `Basic` tab, select `Player Start`, and drag it into the scene and place it at a location of your choice.

Now, with a Player Start Actor in place, select the dropdown under Play, and select `Spawn Player at..` to `Default Player Start`. Now, once you run the Unreal script, it writes the location of the object-of-interest (or the mean of the locations, in case more than one instance is present), and the start location, in the file, and you can now start the game, and it will spawn the new player at your location of choice.

Once you start the game, you can use the Python script `search_sample.py --input_filename <file/generated/by/Unreal/python/script> --output_dir <directory/to/store/dataset/>`. This script first moves the drone to the required height, then takes it near the barrels (they are the current object-of-interest, you can change that by modifying the actor tag being searched for in the `get_static_mesh_locations.py` script), and then completes several orbits around them, modifying the weather conditions after each orbit. The simulation clock has also been sped up, so that the position of sun in the sky changes much faster. You can control those settings in the `search_sample.py` script.

You can tweak the code in the script to alter the filenames, or comment/uncomment the lines in the function `take_snapshot` in `drone_orbit.py` to choose which sensor's data you want to generate.

### Known limitations:
- To the best of my knowledge, at the moment it is not possible to get/set actor locations from Unreal's Python scripting when a game is playing, and neither is it possible to play/pause a game from python.
- While you can start the Unreal Editor using UE4Editor-Cmd.exe and run scripts (see [Unreal's intro to scripting](https://docs.unrealengine.com/en-US/ProductionPipelines/ScriptingAndAutomation/Python/#thecommandline) for examples on how to do it), you can either open the editor and get it to run your code (using `ExecutePythonScript` flag), but it closes immediately after (some simple walk-around should be possible, and needs to be looked at). Similarly, if you use the commandlets method to run scripts, you can potentially run the editor headless, but the levels aren't loaded as they would in the other case, so you need to figure out how to load them before this script will be useful. However, you can use the command line to programmatically open your projects `/path/to/Engine/Binaries/win64/UE4Editor-Cmd.exe /path/to/your/project.uproject`, so that's useful.

### TODO:
- Allow choosing sensor types in command line params, and other params for data collection
- Add support to choose spawn location from multiple PlayerStart actors via Python script
