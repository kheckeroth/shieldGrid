import bpy
import math
import uuid
import copy
# used to create sci-fi inspired art:
#           https://www.instagram.com/p/Cc-wWuNozbk/

# run in Terminal:
#   /Applications/Blender.app/Contents/MacOS/Blender -b -P shieldGrid.py 
#   "C:\Program Files\Blender Foundation\Blender 2.93\blender.exe" -b -P shieldGrid.py
# remove initial cube.
objs = bpy.data.objects
objs.remove(objs["Cube"], do_unlink=True)

columns = 100
rows = 100
timeStep = 0.1
cubes = []
waves = []
frameCount = 500
soundAdjustmentFactor = 1/10
#energySoundFilePath = "C:\\Users\\ken\\Local-Dev\\projects\\blender\\shieldgrid\\energy.wav"
#outputFilePath = 'C:\\Users\\ken\\Local-Dev\\projects\\blender\\shieldgrid'
energySoundFilePath = "/Users/Ken/Local-Dev/miscScripts/blenderAPIprojects/shieldgrid/energy.wav"
outputFilePath = "/Users/Ken/Local-Dev/miscScripts/blenderAPIprojects/shieldgrid"
class Wave:
    def __init__(self, location, direction, amplitude, frequency, wavelength, decayrate):
        self.location = location
        self.direction = direction
        self.amplitude = amplitude
        self.frequency = frequency
        self.wavelength = wavelength
        self.decayrate = decayrate
        self.id = uuid.uuid1()
        self.radius = 0
        self.time = 0
        print('Generating new wave: '+str(self.id))
        print('   amplitude: ' + str(amplitude))
        print('   frequency: ' + str(frequency))
        print('   wavelength: ' + str(wavelength))
        print('   decay: ' + str(decayrate))

class CubeContainer:
    def __init__(self, row, column, cubeObj ,soundObj):
        self.name = "Cube-"+ str(row) + "-" + str(column)
        self.object = cubeObj
        self.soundObj = soundObj
        self.row = row
        self.column = column
        self.initialPosition = copy.copy(self.object.location)
        self.waves = []

    def hasWave(self, waveId):
        for waveLocal in self.waves:
            if (str(waveLocal.id) == str(waveId)):
                return True
        return False


def look_at(obj_camera, point):
    loc_camera = obj_camera.matrix_world.to_translation()
    direction = point - loc_camera
    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj_camera.rotation_euler = rot_quat.to_euler()

def configureBlender():
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.audio_codec = 'MP3'
    scene.frame_end = frameCount
    scene.render.filepath = outputFilePath
    scene.camera.location.x = 0
    scene.camera.location.y = 0
    scene.camera.location.z = 15
    scene.camera.rotation_euler[2] = - scene.camera.rotation_euler[2]

def sceneInit():
    print("initializing scene")
    for c in range(0, rows):
        for d in range(0, columns):
            objName = "Cube-"+ str(c) + "-" + str(d)
            print("   creating: "+ objName)
            
            # Cube creation.
            bpy.ops.mesh.primitive_cube_add(location=(2.0*c, 2.0*d, 0))
            cube = bpy.context.object
            cube.name = objName
            cube.dimensions[0] = 2
            cube.dimensions[1] = 2
            cube.dimensions[2] = 0.2
            
            bpy.ops.object.speaker_add(location=(2.0*c, 2.0*d, 0))
            speaker = bpy.context.object
            speaker.name = objName + "Speaker"
            speaker.data.sound = bpy.data.sounds.load(energySoundFilePath)
            speaker.data.update_tag()
            # add a diffuse material
            diffuseMaterial = bpy.data.materials.new(name=objName+"diff")
            diffuseMaterial.use_nodes = True
            diffuseMaterial.node_tree.nodes.new('ShaderNodeBsdfGlass')
            inp = diffuseMaterial.node_tree.nodes['Material Output'].inputs['Surface']
            outp = diffuseMaterial.node_tree.nodes['Glass BSDF'].outputs['BSDF']
            diffuseMaterial.node_tree.links.new(inp,outp)
            cube.active_material = diffuseMaterial
            diffuseMaterial.diffuse_color = [0,0,0, 1]
            diffuseMaterial.keyframe_insert(data_path='diffuse_color', frame=1, index=-1)
            # add a emission material
            # emission_material = bpy.data.materials.new(name=objName+"emission")
            # emission_material.use_nodes = True
            # material_output = emission_material.node_tree.nodes.get('Material Output')
            # emission = emission_material.node_tree.nodes.new('ShaderNodeEmission')
            # emission.inputs['Strength'].default_value = 1
            # emission_material.node_tree.links.new(material_output.inputs[0], emission.outputs[0])

            cubeTmp = CubeContainer(c,d, cube, speaker)
            cubes.append(cubeTmp)

def propogateWaves():
    for wave in waves:
        # expand the wave
        # find cubes within radius that do not contain the wave, then add it.
        wave.radius += wave.wavelength*wave.frequency
        for cube in cubes:
            if math.dist(cube.object.location, wave.location) < wave.radius and not cube.hasWave(wave.id):
                waveTmp = copy.copy(wave)
                waveTmp.time = 0
                cube.waves.append(waveTmp)
    
    # update the position of all cubes
    for cube in cubes:
        displacement_x = 0
        displacement_y = 0
        displacement_z = 0
        for wave in cube.waves:
            displacement = math.exp(-wave.decayrate*wave.time)*wave.amplitude*math.sin(wave.frequency*wave.time)
            # v = wavelength / T, T = wavelength/ v
            # y = e^(-gamma*t)*A*Cos(omega*t - alpha)
            # http://hyperphysics.phy-astr.gsu.edu/hbase/oscda.html
            wave.time += timeStep
            displacement_x += displacement * wave.direction[0]
            displacement_y += displacement * wave.direction[1]
            displacement_z += displacement * wave.direction[2]

        cube.object.location[0] = cube.initialPosition[0] + displacement_x
        cube.object.location[1] = cube.initialPosition[1] + displacement_y
        cube.object.location[2] = cube.initialPosition[2] + displacement_z

        cube.soundObj.location[0] = cube.initialPosition[0] + displacement_x
        cube.soundObj.location[1] = cube.initialPosition[1] + displacement_y
        cube.soundObj.location[2] = cube.initialPosition[2] + displacement_z

        displacement = math.dist([displacement_x, displacement_y, displacement_z], [0,0,0])
        cube.soundObj.data.volume = 1 if displacement*soundAdjustmentFactor > 1 else 0 if displacement*soundAdjustmentFactor < 0.01 else displacement*soundAdjustmentFactor
        # material_strength = displacement
        # if (material_strength) > 0:
        #     bpy.data.materials[cube.name+"diff"].diffuse_color = [displacement_x, displacement_y , displacement_z, 1]
        #     bpy.data.materials[cube.name+"diff"].keyframe_insert(data_path='diffuse_color')
        #     bpy.data.materials[cube.name].node_tree.nodes["Emission"].inputs[1].default_value =  material_strength
        #     bpy.data.materials[cube.name].node_tree.nodes["Emission"].inputs[1].keyframe_insert(data_path='default_value')
        #     if (cube.row == 0 and cube.column == 0):
        #         print('setting '+cube.name + ' material: '+ str(material_strength))
        cube.object.keyframe_insert(data_path='location')
        cube.soundObj.keyframe_insert(data_path='location')
        cube.soundObj.data.keyframe_insert("volume")

configureBlender()
sceneInit()

obj_camera = bpy.data.objects["Camera"]

waves.append(Wave(location = [0, 0, 0],direction =  [0, 0, -1], amplitude = 5, frequency = 1, wavelength = 2, decayrate = 0.1))
waves.append(Wave(location = [50, 0, 0],direction =  [0, 0, 1], amplitude = 5, frequency = 1, wavelength = 2, decayrate = 0.1))

for frame in range(0, frameCount):
    print("creating frame: " + str(frame))
    if frame == 100:
        waves.append(Wave(location = [0, 100, 0],direction =  [1, 0, 1], amplitude = 5, frequency = 0.5, wavelength = 2, decayrate = 0.1))
    bpy.context.scene.frame_set(frame)
    propogateWaves()
bpy.context.scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath="output.blend")
#bpy.ops.render.render(animation=True, use_viewport=True)