import bpy
import sys

limit_number = 15000
sys.setrecursionlimit(limit_number)

prevCollections = {}
virtualObjs = []

root_collection = bpy.context.scene.collection

if "unity_export" not in bpy.context.scene.collection.children.keys():
    unity_collection = bpy.context.blend_data.collections.new(name='unity_export')
    root_collection.children.link(unity_collection)
else:
    unity_collection = bpy.context.scene.collection.children['unity_export']


def linkToObject(obj, parentObj):
    prevCollections[obj] = obj.users_collection[0]

    obj.parent = parentObj
    obj.users_collection[0].objects.unlink(bpy.data.objects[obj.name])
    parentObj.users_collection[0].objects.link(bpy.data.objects[obj.name])


def linkToCollection(obj, col):
    prevCollections[obj] = obj.users_collection[0]

    obj.users_collection[0].objects.unlink(bpy.data.objects[obj.name])
    col.objects.link(bpy.data.objects[obj.name])


def restore_scene():
    for obj, col in prevCollections.items():
        linkToCollection(obj, col)

    for vObj in virtualObjs:
        if vObj in bpy.data.objects:
            bpy.data.objects[vObj].select_set(True)
            bpy.ops.object.delete()

def createVirtualObject(col):
    bpy.ops.mesh.primitive_plane_add(size=0, enter_editmode=False, align='WORLD', location=(0, 0, 0))
    bpy.context.active_object.name = col.name

    virtualObj = bpy.data.objects[col.name]
    virtualObjs.append(virtualObj.name)

    return virtualObj

# asume parent's virtual object is created outside
def findChild_N_attach(parent):
    virtualParent = bpy.data.objects[parent.name]

    for child in parent.children:
        virtualChild = createVirtualObject(child)
        linkToObject(virtualChild, virtualParent)

        findChild_N_attach(child)

    for obj in parent.objects:
        linkToObject(obj, virtualParent)

def preProcessScene():
    for col in root_collection.children:
        if col.name == "unity_export":
            continue

        virtualObj = createVirtualObject(col)
        linkToCollection(virtualObj, unity_collection)
        findChild_N_attach(col)

    for obj in root_collection.objects:
        linkToCollection(obj, unity_collection)

preProcessScene()

blender249 = True
blender280 = (2,80,0) <= bpy.app.version

try:
    import Blender
except:
    blender249 = False

if not blender280:
    if blender249:
        try:
            import export_fbx
        except:
            print('error: export_fbx not found.')
            Blender.Quit()
    else :
        try:
            import io_scene_fbx.export_fbx
        except:
            print('error: io_scene_fbx.export_fbx not found.')
            # This might need to be bpy.Quit()
            raise

# Find the Blender output file
import os
outfile = os.getenv("UNITY_BLENDER_EXPORTER_OUTPUT_FILE")

# Do the conversion
print("Starting blender to FBX conversion " + outfile)

if blender280:
    import bpy.ops
    bpy.ops.export_scene.fbx(filepath=outfile,
        check_existing=False,
        use_selection=False,
        use_active_collection=False,
        object_types= {'ARMATURE','CAMERA','LIGHT','MESH','OTHER','EMPTY'},
        use_mesh_modifiers=True,
        mesh_smooth_type='OFF',
        use_custom_props=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        apply_scale_options='FBX_SCALE_ALL')
elif blender249:
    mtx4_x90n = Blender.Mathutils.RotationMatrix(-90, 4, 'x')
    export_fbx.write(outfile,
        EXP_OBS_SELECTED=False,
        EXP_MESH=True,
        EXP_MESH_APPLY_MOD=True,
        EXP_MESH_HQ_NORMALS=True,
        EXP_ARMATURE=True,
        EXP_LAMP=True,
        EXP_CAMERA=True,
        EXP_EMPTY=True,
        EXP_IMAGE_COPY=False,
        ANIM_ENABLE=True,
        ANIM_OPTIMIZE=False,
        ANIM_ACTION_ALL=True,
        GLOBAL_MATRIX=mtx4_x90n)
else:
    # blender 2.58 or newer
    import math
    from mathutils import Matrix
    # -90 degrees
    mtx4_x90n = Matrix.Rotation(-math.pi / 2.0, 4, 'X')

    class FakeOp:
        def report(self, tp, msg):
            print("%s: %s" % (tp, msg))

    exportObjects = ['ARMATURE', 'EMPTY', 'MESH']

    minorVersion = bpy.app.version[1];
    if minorVersion <= 58:
        # 2.58
        io_scene_fbx.export_fbx.save(FakeOp(), bpy.context, filepath=outfile,
            global_matrix=mtx4_x90n,
            use_selection=False,
            object_types=exportObjects,
            mesh_apply_modifiers=True,
            ANIM_ENABLE=True,
            ANIM_OPTIMIZE=False,
            ANIM_OPTIMIZE_PRECISSION=6,
            ANIM_ACTION_ALL=True,
            batch_mode='OFF',
            BATCH_OWN_DIR=False)
    else:
        # 2.59 and later
        kwargs = io_scene_fbx.export_fbx.defaults_unity3d()
        io_scene_fbx.export_fbx.save(FakeOp(), bpy.context, filepath=outfile, **kwargs)
    # HQ normals are not supported in the current exporter

print("Finished blender to FBX conversion " + outfile)

restore_scene()