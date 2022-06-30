from PLL_Lib import Picoscope

# Connect to the Picoscope
with Picoscope() as scope:
    # Keep capturing traces until the a key is pressed
    scope.wait_for_key('a')
# The Picoscope will automatically be disconnected at the end of the indented block.