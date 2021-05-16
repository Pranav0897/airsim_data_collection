Unreal extends its functionality by providing API calls in Python. However, there's a major caveat to this: you can only work with the blueprint before a game is running; as far as I can tell, you can't make the game play or pause from the python script, nor access actor locations when the game is running.

So, to get the actor locations, we create a python script which utilizes unreal's API to get actor locations before we start the game. We can do this two ways:
- Add the script as a startup script to the project. That way, when you open up the project in Unreal Editor, this script runs in the background, and stores the locations of the barrel, and the starting point in a file which the airsim script can then access when running later. To do this:
Select Edit > Project Settings.... Under the Plugins list, select Python. Then, add your scripts to the Startup scripts setting:
![]
Restart the Unreal Editor when done. The next time the Editor loads your Project, it should run your new startup scripts.
- 