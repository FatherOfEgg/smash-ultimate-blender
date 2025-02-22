import json
import os
import os.path
from tokenize import String
import bpy
import mathutils
import time
import math

from .. import ssbh_data_py
import numpy as np
from pathlib import Path

from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper
from bpy_extras import image_utils

from ..operators import master_shader, material_inputs

import sqlite3

class ImportModelPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ultimate'
    bl_label = 'Model Importer'
    bl_options = {'DEFAULT_CLOSED'}

    '''
    def find_model_files(self, context):
        all_files = os.listdir(context.scene.sub_model_folder_path)
        model_files = [file for file in all_files if 'model' in file]
        for model_file in model_files:
            extension = model_file.split('.')[1]
            if 'numshb' == extension:
                context.scene.sub_model_numshb_file_name = model_file
            elif 'nusktb' == extension:
                context.scene.sub_model_nusktb_file_name = model_file
            elif 'numdlb' == extension:
                context.scene.sub_model_numdlb_file_name = model_file
    '''
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        
        if '' == context.scene.sub_model_folder_path:
            row = layout.row(align=True)
            row.label(text='Please select a folder...')
            row = layout.row(align=True)
            row.operator('sub.ssbh_model_folder_selector', icon='ZOOM_ALL', text='Browse for the model folder')
            return
        
        row = layout.row(align=True)
        row.label(text='Selected Folder: "' + context.scene.sub_model_folder_path +'"')
        row = layout.row(align=True)
        row.operator('sub.ssbh_model_folder_selector', icon='ZOOM_ALL', text='Browse for a different model folder')

        all_requirements_met = True
        min_requirements_met = True
        if '' == context.scene.sub_model_numshb_file_name:
            row = layout.row(align=True)
            row.alert = True
            row.label(text='No .numshb file found! Cannot import without it!', icon='ERROR')
            all_requirements_met = False
            min_requirements_met = False

        else:
            row = layout.row(align=True)
            row.alert = False
            row.label(text='NUMSHB file: "' + context.scene.sub_model_numshb_file_name+'"', icon='FILE')

        if '' == context.scene.sub_model_nusktb_file_name:
            row = layout.row(align=True)
            row.alert = True
            row.label(text='No .nusktb file found! Cannot import without it!', icon='ERROR')
            all_requirements_met = False
            min_requirements_met = False
        else:
            row = layout.row(align=True)
            row.alert = False
            row.label(text='NUSKTB file: "' + context.scene.sub_model_nusktb_file_name+'"', icon='FILE')

        if '' == context.scene.sub_model_numdlb_file_name:
            row = layout.row(align=True)
            row.alert = True
            row.label(text='No .numdlb file found! Can import, but without materials...', icon='ERROR')
            all_requirements_met = False
        else:
            row = layout.row(align=True)
            row.alert = False
            row.label(text='NUMDLB file: "' + context.scene.sub_model_numdlb_file_name+'"', icon='FILE')

        if '' ==  context.scene.sub_model_numatb_file_name:
            row = layout.row(align=True)
            row.alert = True
            row.label(text='No .numatb file found! Can import, but without materials...', icon='ERROR')
            all_requirements_met = False
        else:
            row = layout.row(align=True)
            row.alert = False
            row.label(text='NUMATB file: "' + context.scene.sub_model_numatb_file_name+'"', icon='FILE')

        if not min_requirements_met:
            row = layout.row(align=True)
            row.alert = True
            row.label(text='Needs .NUMSHB and .NUSKTB at a minimum to import!', icon='ERROR')
            return
        elif not all_requirements_met:
            row = layout.row(align=True)
            row.operator('sub.model_importer', icon='IMPORT', text='Limited Model Import')
        else:
            row = layout.row(align=True)
            row.operator('sub.model_importer', icon='IMPORT', text='Import Model')
        

class ModelFolderSelector(bpy.types.Operator, ImportHelper):
    bl_idname = 'sub.ssbh_model_folder_selector'
    bl_label = 'Folder Selector'

    filter_glob: StringProperty(
        default='',
        options={'HIDDEN'}
    )
    """
    Cancelled until further notice.
    merge_same_name_meshes: BoolProperty(
        name="Merge Same Name Meshes",
        description="Merge Same Name Meshes",
        default=True,
    )   
    """

    # Initially set the filename field to be nothing
    def invoke(self, context, _event):
        self.filepath = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        context.scene.sub_model_numshb_file_name = '' 
        context.scene.sub_model_nusktb_file_name = '' 
        context.scene.sub_model_numdlb_file_name = '' 
        context.scene.sub_model_numatb_file_name = ''  
        #context.scene.sub_merge_same_name_meshes = self.merge_same_name_meshes
        #print(self.filepath)
        context.scene.sub_model_folder_path = self.filepath
        all_files = os.listdir(context.scene.sub_model_folder_path)
        model_files = [file for file in all_files if 'model' in file]
        for model_file in model_files:
            print(model_file)
            name, extension = os.path.splitext(model_file)
            print(extension)
            if '.numshb' == extension:
                context.scene.sub_model_numshb_file_name = model_file
            elif '.nusktb' == extension:
                context.scene.sub_model_nusktb_file_name = model_file
            elif '.numdlb' == extension:
                context.scene.sub_model_numdlb_file_name = model_file
            elif '.numatb' == extension:
                context.scene.sub_model_numatb_file_name = model_file
            elif '.nuhlpb' == extension:
                context.scene.sub_model_nuhlpb_file_name = model_file
        return {'FINISHED'}

class ModelImporter(bpy.types.Operator):
    bl_idname = 'sub.model_importer'
    bl_label = 'Model Importer'

    def execute(self, context):
        start = time.time()

        import_model(self,context)

        end = time.time()
        print(f'Imported model in {end - start} seconds')
        return {'FINISHED'}

def import_model(self, context):
    dir = context.scene.sub_model_folder_path
    numdlb_name = context.scene.sub_model_numdlb_file_name
    numshb_name = context.scene.sub_model_numshb_file_name
    nusktb_name = context.scene.sub_model_nusktb_file_name
    numatb_name = context.scene.sub_model_numatb_file_name
    nuhlpb_name = context.scene.sub_model_nuhlpb_file_name

    start = time.time()
    ssbh_model = ssbh_data_py.modl_data.read_modl(dir + numdlb_name) if numdlb_name != '' else None

    # Numpy provides much faster performance than Python lists.
    # TODO(SMG): This API for ssbh_data_py will likely have changes and improvements in the future.
    ssbh_mesh = ssbh_data_py.mesh_data.read_mesh(dir + numshb_name, use_numpy=True) if numshb_name != '' else None

    ssbh_skel = ssbh_data_py.skel_data.read_skel(dir + nusktb_name) if numshb_name != '' else None
    ssbh_matl = ssbh_data_py.matl_data.read_matl(dir + numatb_name) if numatb_name != '' else None
    nuhlpb_json = read_nuhlpb_json(dir + nuhlpb_name) if nuhlpb_name != '' else None
    end = time.time()
    print(f'Read files in {end - start} seconds')

    armature = create_armature(ssbh_skel, context)
    created_meshes = create_mesh(ssbh_model, ssbh_matl, ssbh_mesh, ssbh_skel, armature, context)
    import_nuhlpb_data_from_json(nuhlpb_json, armature, context)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return

def get_ssbh_lib_json_exe_path():
    # Use the Path class to handle path differences between Windows, Linux, and MacOS.
    this_file_path = Path(__file__)
    return this_file_path.parent.parent.joinpath('ssbh_lib_json').joinpath('ssbh_lib_json.exe').resolve()

def get_shader_db_file_path():
    # This file was generated with duplicates removed to optimize space.
    # https://github.com/ScanMountGoat/Smush-Material-Research#shader-database
    this_file_path = Path(__file__)
    return this_file_path.parent.parent.joinpath('shader_file').joinpath('Nufx.db').resolve()


'''
The following code is mostly shamelessly stolen from SMG 
(except for the bone import)
Oh hey SMG is a collaborator of this repo now, and you cant steal code from a collaborator ;)
'''
def get_matrix4x4_blender(ssbh_matrix):
    return mathutils.Matrix(ssbh_matrix).transposed()

def find_bone(skel, name):
    for bone in skel.bones:
        if bone.name == name:
            return bone

    return None


def find_bone_index(skel, name):
    for i, bone in enumerate(skel.bones):
        if bone.name == name:
            return i

    return None

def get_name_from_index(index, bones):
    if index is None:
        return None
    return bones[index].name

def get_index_from_name(name, bones):
    for index, bone in enumerate(bones):
        if bone.name == name:
            return index

def reorient(m, transpose=True):
    from mathutils import Matrix
    m = Matrix(m)

    if transpose:
        m.transpose()
     
    c00,c01,c02,c03 = m[0]
    c10,c11,c12,c13 = m[1]
    c20,c21,c22,c23 = m[2]
    c30,c31,c32,c33 = m[3]
    
    m = Matrix([
        [c11, -c10, -c12, -c13],
        [ -c01, c00, c02, c03],
        [ -c21, c20, c22, c23],
        [ c30, c31, c32, c33]
    ])

    return m 

def reorient_root(m, transpose=True):
    from mathutils import Matrix
    m = Matrix(m)
    
    if transpose:
        m.transpose() 
      
    c00,c01,c02,c03 = m[0]
    c10,c11,c12,c13 = m[1]
    c20,c21,c22,c23 = m[2]
    c30,c31,c32,c33 = m[3]
    
    # TODO: Find out if the following does not work for certain skels
    m = Matrix([
        [0.0, 1.0, 0.0, 0.0],
        [ 0.0, 0.0, -1.0, 0.0],
        [ -1.0, 0.0, 0.0, 0.0],
        [ 0.0, 0.0, 0.0, 1.0]
    ])
    
    return m


def create_armature(ssbh_skel, context): 
    '''
    So blender bone matrixes are not relative to their parent, unlike the ssbh skel.
    Also, blender has a different coordinate system for the bones.
    Also, ssbh matrixes need to be transposed first.
    Also, the root bone needs to be modified differently to fix the world orientation
    Also, the ssbh bones are not guaranteed to appear in 'heirarchal' order, 
                 which is where the parent always appears before the child.
    Also, iterating through the blender bones appears to preserve the order of insertion,
                 so its also not gauranteed heirarchal order.
    '''
    start = time.time()
    
    # Create a new armature and select it.
    base_skel_name = "smush_blender_import"
    armature = bpy.data.objects.new(base_skel_name, bpy.data.armatures.new(base_skel_name))
    armature.rotation_mode = 'QUATERNION'
    armature.show_in_front = True
    armature.data.display_type = 'STICK'
    context.view_layer.active_layer_collection.collection.objects.link(armature)
    context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    
    bone_name_parent_name_dict = {bone.name:get_name_from_index(bone.parent_index, ssbh_skel.bones) for bone in ssbh_skel.bones}
    
    edit_bones = armature.data.edit_bones

    # Make Bones
    for ssbh_bone in ssbh_skel.bones:
        blender_bone = edit_bones.new(ssbh_bone.name)
        blender_bone.head = [0,0,0]
        blender_bone.tail = [0,1,0] # Doesnt actually matter where its pointing, it just needs to point somewhere

    # Assign Parents
    for ssbh_bone in ssbh_skel.bones:  
        blender_bone = edit_bones.get(ssbh_bone.name)
        parent_bone_name = bone_name_parent_name_dict[ssbh_bone.name]
        if parent_bone_name is None:
            continue
        parent_bone = edit_bones.get(parent_bone_name, None)
        blender_bone.parent = parent_bone

    # Get a list of bones in 'heirarchal' order
    def heirarchy_order(bone, reordered):
        if bone not in reordered:
            reordered.append(bone)
        for child in bone.children:
            heirarchy_order(child, reordered)
    reordered = []
    heirarchy_order(edit_bones[0], reordered)

    # Transform bones    
    for blender_bone in reordered:
        ssbh_bone = ssbh_skel.bones[get_index_from_name(blender_bone.name, ssbh_skel.bones)]
        if blender_bone.parent is None:
            blender_bone.matrix = reorient_root(ssbh_bone.transform)
            continue
        blender_bone.matrix = blender_bone.parent.matrix @ reorient(ssbh_bone.transform)
    

    # fix bone lengths
    for blender_bone in reordered:
        if "H_" == blender_bone.name[:2]:
            continue

        if len(blender_bone.children) == 0:
            if blender_bone.parent:
                blender_bone.length = blender_bone.parent.length
            continue
        
        if len(blender_bone.children) == 1:
            if blender_bone.head == blender_bone.children[0].head:
                continue
            blender_bone.length = (blender_bone.head - blender_bone.children[0].head).length
            continue
        
        for child in blender_bone.children:
            if child.name == blender_bone.name + '_eff':
                blender_bone.length = (blender_bone.head - child.head).length

        finger_base_bones = ['FingerL10','FingerL20', 'FingerL30','FingerL40',
                             'FingerR10','FingerR20', 'FingerR30','FingerR40',]
        if any(finger_base_bone == blender_bone.name for finger_base_bone in finger_base_bones):
            finger_1_bone = edit_bones.get(blender_bone.name[:-1]+'1')
            if finger_1_bone:
                blender_bone.length = (blender_bone.head - finger_1_bone.head).length
        
        if blender_bone.name == 'ArmL' or blender_bone.name == 'ArmR':
            hand_bone = edit_bones.get("Hand" + blender_bone.name[-1])
            if hand_bone:
                blender_bone.length = (blender_bone.head - hand_bone.head).length
        
        if blender_bone.name == 'ShoulderL' or blender_bone.name == 'ShoulderR':
            arm_bone = edit_bones.get("Arm" + blender_bone.name[-1])
            if arm_bone:
                blender_bone.length = (blender_bone.head - arm_bone.head).length

        if blender_bone.name == 'LegR' or blender_bone.name == 'LegL':
            knee_bone = edit_bones.get('Knee' + blender_bone.name[-1])
            if knee_bone:
                blender_bone.length = (blender_bone.head - knee_bone.head).length
        
        if blender_bone.name == 'KneeR' or blender_bone.name == 'KneeL':
            foot_bone = edit_bones.get('Foot' + blender_bone.name[-1])
            if foot_bone:
                blender_bone.length = (blender_bone.head - foot_bone.head).length
        
        if blender_bone.name == 'ClavicleC':
            neck_bone = edit_bones.get('Neck')
            if neck_bone:
                blender_bone.length = (blender_bone.head - neck_bone.head).length

    # Assign bone colors and bone layers
    bpy.ops.object.mode_set(mode='POSE')
    
    default_group = bpy.context.object.pose.bone_groups.new()
    default_group.name = 'Default'
    default_group.color_set = 'DEFAULT'

    helper_group = bpy.context.object.pose.bone_groups.new()
    helper_group.name = 'Helper'
    helper_group.color_set = 'THEME06'

    swing_group = bpy.context.object.pose.bone_groups.new()
    swing_group.name = 'Swing'
    swing_group.color_set = 'THEME04'

    system_group = bpy.context.object.pose.bone_groups.new()
    system_group.name = 'System'
    system_group.color_set = 'THEME10'

    system_bone_names = ['Trans', 'Rot', 'Throw']
    system_bone_suffixes = ['_null', '_eff', '_offset']
    for bone in bpy.context.object.pose.bones:
        bone.bone.layers[16] = True
        if 'H_' == bone.name[:2]:
            bone.bone_group = helper_group
            bone.bone.layers[2] = True
        elif 'S_' == bone.name[:2]:
            bone.bone.layers[1] = True
            bone.bone.layers[17] = True
            bone.bone_group = swing_group
            if '_null' in bone.name:
                bone.bone_group = system_group
                bone.bone.layers[16] = False
                bone.bone.layers[17] = False
                bone.bone.use_deform = False
        else:
            bone.bone_group = default_group
            if any(system_bone_name == bone.name for system_bone_name in system_bone_names) \
            or any(system_bone_suffix in bone.name for system_bone_suffix in system_bone_suffixes):
                bone.bone_group = system_group
                bone.bone.layers[16] = False
                bone.bone.layers[17] = False
                bone.bone.use_deform = False


    
    bpy.ops.object.mode_set(mode='OBJECT')
    end = time.time()
    print(f'Created armature in {end - start} seconds')

    return armature


def attach_armature_create_vertex_groups(mesh_obj, skel, armature, ssbh_mesh_object):
    from math import radians
    from mathutils import Matrix
    if skel is not None:
        # Create vertex groups for each bone to support skinning.
        for bone in skel.bones:
            mesh_obj.vertex_groups.new(name=bone.name)

        # Apply the initial parent bone transform if present.
        parent_bone = find_bone(skel, ssbh_mesh_object.parent_bone_name)
        if parent_bone is not None:
            world_transform = skel.calculate_world_transform(parent_bone)
            mesh_obj.matrix_world = get_matrix4x4_blender(world_transform)

            # Use regular skin weights for mesh objects parented to a bone.
            # TODO: Should this only apply if there are no influences?
            # TODO: Should this be handled by actual parenting in Blender?
            mesh_obj.vertex_groups[parent_bone.name].add(ssbh_mesh_object.vertex_indices, 1.0, 'REPLACE')
        else:
            # Set the vertex skin weights for each bone.
            # TODO: Is there a faster way than setting weights per vertex?
            for influence in ssbh_mesh_object.bone_influences:
                # TODO: Will influences always refer to valid bones in the skeleton?
                vertex_group = mesh_obj.vertex_groups[influence.bone_name]
                for w in influence.vertex_weights:
                    vertex_group.add([w.vertex_index], w.vertex_weight, 'REPLACE')
        # Fix the rotation of the mesh objects. 
        # TODO: Figure out how to apply all transforms.
        trans_vec, rot_vec, scale_vec = mesh_obj.matrix_world.decompose()
        trans_mat = Matrix.Translation(trans_vec)
        rot_mat = rot_vec.to_matrix().to_4x4()
        scale_mat = Matrix.Scale(scale_vec[0],4,(1,0,0)) * Matrix.Scale(scale_vec[1],4,(0,1,0)) * Matrix.Scale(scale_vec[2],4,(0,0,1)) # theres gotta be a better way of doing this
        axis_correction = Matrix.Rotation(radians(90), 4, 'X')  
        mesh_obj.matrix_world = axis_correction @ trans_mat @ rot_mat @ scale_mat

    # Attach the mesh object to the armature object.
    if armature is not None:
        mesh_obj.parent = armature
        for bone in armature.data.bones.values():
            mesh_obj.vertex_groups.new(name=bone.name)
        modifier = mesh_obj.modifiers.new(armature.data.name, type="ARMATURE")
        modifier.object = armature


def create_blender_mesh(ssbh_mesh_object, skel, name_index_mat_dict):
    blender_mesh = bpy.data.meshes.new(ssbh_mesh_object.name)

    # TODO: Handle attribute data arrays not having the appropriate number of rows and columns.
    # This won't be an issue for in game models.

    # Using foreach_set is much faster than bmesh or from_pydata.
    # https://devtalk.blender.org/t/alternative-in-2-80-to-create-meshes-from-python-using-the-tessfaces-api/7445/3
    positions = ssbh_mesh_object.positions[0].data[:,:3]
    blender_mesh.vertices.add(positions.shape[0])
    blender_mesh.vertices.foreach_set("co", positions.flatten())

    # Assume triangles, which is the only primitive used in Smash Ultimate.
    # TODO(SMG): ssbh_data_py can use a numpy array here in the future.
    vertex_indices = np.array(ssbh_mesh_object.vertex_indices, dtype=np.int32)
    loop_start = np.arange(0, vertex_indices.shape[0], 3, dtype=np.int32)
    loop_total = np.full(loop_start.shape[0], 3, dtype=np.int32)

    blender_mesh.loops.add(vertex_indices.shape[0])
    blender_mesh.loops.foreach_set("vertex_index", vertex_indices)

    blender_mesh.polygons.add(loop_start.shape[0])
    blender_mesh.polygons.foreach_set("loop_start", loop_start)
    blender_mesh.polygons.foreach_set("loop_total", loop_total)

    for attribute_data in ssbh_mesh_object.texture_coordinates:
        uv_layer = blender_mesh.uv_layers.new(name=attribute_data.name)

        # Flip vertical.
        uvs = attribute_data.data[:,:2].copy()
        uvs[:,1] = 1.0 - uvs[:,1]

        # This is set per loop rather than per vertex.
        loop_uvs = uvs[vertex_indices].flatten()
        uv_layer.data.foreach_set("uv", loop_uvs)

    for attribute_data in ssbh_mesh_object.color_sets:
        color_layer = blender_mesh.vertex_colors.new(name=attribute_data.name)
        # TODO: Create a function for this?
        colors = attribute_data.data[:,:4]

        # This is set per loop rather than per vertex.
        loop_colors = colors[vertex_indices].flatten()
        color_layer.data.foreach_set("color", loop_colors)

    # These calls are necessary since we're setting mesh data manually.
    blender_mesh.update()
    blender_mesh.validate()

    # TODO: Is there a faster way to do this?
    # Now that the mesh is created, now we can assign split custom normals
    blender_mesh.use_auto_smooth = True # Required to use custom normals
    blender_mesh.normals_split_custom_set_from_vertices(ssbh_mesh_object.normals[0].data[:,:3])

    # Try and assign the material.
    # Mesh import should still succeed even if materials couldn't be created.
    # Users can still choose to not export the matl.
    # TODO: Report errors to the user?
    try:
        material = name_index_mat_dict[(ssbh_mesh_object.name, ssbh_mesh_object.sub_index)]
        blender_mesh.materials.append(material)
    except Exception as e:
        print(f'Failed to assign material for {ssbh_mesh_object.name}{ssbh_mesh_object.sub_index}: {e}')


    return blender_mesh


def create_mesh(ssbh_model, ssbh_matl, ssbh_mesh, ssbh_skel, armature, context):
    '''
    So the goal here is to create a set of materials to share among the meshes for this model.
    But, other previously created models can have materials of the same name.
    Gonna make sure not to conflict.
    example, bpy.data.materials.new('A') might create 'A' or 'A.001', so store reference to the mat created rather than the name
    '''
    created_meshes = []
    unique_numdlb_material_labels = {e.material_label for e in ssbh_model.entries}
    
    # Make Master Shader if its not already made
    master_shader.create_master_shader()

    texture_name_to_image_dict = {}
    texture_name_to_image_dict = import_material_images(ssbh_matl, context)

    label_to_material_dict = {}
    for label in unique_numdlb_material_labels:
        blender_mat = bpy.data.materials.new(label)

        # Mesh import should still succeed even if materials can't be created.
        # TODO: Report some sort of error to the user?
        try:
            setup_blender_mat(blender_mat, label, ssbh_matl, texture_name_to_image_dict)
            label_to_material_dict[label] = blender_mat
        except Exception as e:
            print(f'Failed to create material for {label}: {e}')

    name_index_mat_dict = { 
        (e.mesh_object_name,e.mesh_object_sub_index):label_to_material_dict[e.material_label] 
        for e in ssbh_model.entries if e.material_label in label_to_material_dict
    }

    start = time.time()

    for i, ssbh_mesh_object in enumerate(ssbh_mesh.objects):
        blender_mesh = create_blender_mesh(ssbh_mesh_object, ssbh_skel, name_index_mat_dict)
        mesh_obj = bpy.data.objects.new(blender_mesh.name, blender_mesh)

        attach_armature_create_vertex_groups(mesh_obj, ssbh_skel, armature, ssbh_mesh_object)
        mesh_obj["numshb order"] = i
        context.collection.objects.link(mesh_obj)
        created_meshes.append(mesh_obj)
    
    end = time.time()
    print(f'Created meshes in {end - start} seconds')

    return created_meshes

def import_material_images(ssbh_matl, context):
    texture_name_to_image_dict = {}
    texture_name_set = set()

    for ssbh_mat_entry in ssbh_matl.entries:
        for attribute in ssbh_mat_entry.textures:
            texture_name_set.add(attribute.data)

    print('texture_name_set = %s' % texture_name_set)

    for texture_name in texture_name_set:
        dir = context.scene.sub_model_folder_path
        image = image_utils.load_image(texture_name + '.png', dir, place_holder=True, check_existing=False)  
        texture_name_to_image_dict[texture_name] = image

    return texture_name_to_image_dict


def enable_inputs(node_group_node, param_id):
    for input in node_group_node.inputs:
        if input.name.split(' ')[0] == param_id:
            input.hide = False


def get_vertex_attributes(node_group_node, shader_name):
    # Query the shader database for attribute information.
    # Using SQLite is much faster than iterating through the JSON dump.
    with sqlite3.connect(get_shader_db_file_path()) as con:
        # Construct a query to find all the vertex attributes for this shader.
        # Invalid shaders will return an empty list.
        sql = """
            SELECT v.AttributeName 
            FROM VertexAttribute v 
            INNER JOIN ShaderProgram s ON v.ShaderProgramID = s.ID 
            WHERE s.Name = ?
            """
        # The database has a single entry for each program, so don't include the render pass tag.
        return [row[0] for row in con.execute(sql, (shader_name[:len('SFX_PBS_0000000000000080')],)).fetchall()]


def setup_blender_mat(blender_mat, material_label, ssbh_matl: ssbh_data_py.matl_data.MatlData, texture_name_to_image_dict):
    # TODO: Handle none?
    entry = None
    for ssbh_mat_entry in ssbh_matl.entries:
        if ssbh_mat_entry.material_label == material_label:
            entry = ssbh_mat_entry

    # Change Mat Settings
    # Change Transparency Stuff Later
    blender_mat.blend_method = 'CLIP'
    blender_mat.use_backface_culling = True
    blender_mat.show_transparent_back = False
    # TODO: This should be based on the blend state and not the shader label.
    alpha_blend_suffixes = ['_far', '_sort', '_near']
    if any(suffix in entry.shader_label for suffix in alpha_blend_suffixes):
        blender_mat.blend_method = 'BLEND'
        
    # Clone Master Shader
    master_shader_name = master_shader.get_master_shader_name()
    master_node_group = bpy.data.node_groups.get(master_shader_name)
    clone_group = master_node_group.copy()

    # Setup Clone
    clone_group.name = entry.shader_label

    # Add our new Nodes
    blender_mat.use_nodes = True
    nodes = blender_mat.node_tree.nodes
    links = blender_mat.node_tree.links

    # Cleanse Node Tree
    nodes.clear()
    
    material_output_node = nodes.new('ShaderNodeOutputMaterial')
    material_output_node.location = (900,0)
    node_group_node = nodes.new('ShaderNodeGroup')
    node_group_node.name = 'smash_ultimate_shader'
    node_group_node.width = 600
    node_group_node.location = (-300, 300)
    node_group_node.node_tree = clone_group
    for input in node_group_node.inputs:
        input.hide = True
    shader_label = node_group_node.inputs['Shader Label']
    shader_label.hide = False
    shader_name = entry.shader_label
    shader_label.default_value = entry.shader_label
    material_label = node_group_node.inputs['Material Name']
    material_label.hide = False
    material_label.default_value = entry.material_label

    # TODO: Refactor this to be cleaner?
    blend_state = entry.blend_states[0].data
    enable_inputs(node_group_node, entry.blend_states[0].param_id.name)

    blend_state_inputs = []
    for input in node_group_node.inputs:
        if input.name.split(' ')[0] == 'BlendState0':
            blend_state_inputs.append(input)
            
    for input in blend_state_inputs:
        field_name = input.name.split(' ')[1]
        if field_name == 'Field1':
            input.default_value = blend_state.source_color.name
        if field_name == 'Field3':
            input.default_value = blend_state.destination_color.name
        if field_name == 'Field7':
            input.default_value = blend_state.alpha_sample_to_coverage

    rasterizer_state = entry.rasterizer_states[0].data
    enable_inputs(node_group_node, entry.rasterizer_states[0].param_id.name)

    rasterizer_state_inputs = [input for input in node_group_node.inputs if input.name.split(' ')[0] == 'RasterizerState0']
    for input in rasterizer_state_inputs:
        field_name = input.name.split(' ')[1]
        if field_name == 'Field1':
            input.default_value = rasterizer_state.fill_mode.name
        if field_name == 'Field2':
            input.default_value = rasterizer_state.cull_mode.name
        if field_name == 'Field3':
            input.default_value = rasterizer_state.depth_bias

    for param in entry.booleans:
        input = node_group_node.inputs.get(param.param_id.name)
        input.hide = False
        input.default_value = param.data

    for param in entry.floats:
        input = node_group_node.inputs.get(param.param_id.name)
        input.hide = False
        input.default_value = param.data
    
    for param in entry.vectors:
        param_name = param.param_id.name

        if param_name in material_inputs.vec4_param_to_inputs:
            # Find and enable inputs.
            inputs = [node_group_node.inputs.get(name) for _, name, _ in material_inputs.vec4_param_to_inputs[param_name]]
            for input in inputs:
                input.hide = False

            # Assume inputs are RGBA, RGB/A, or X/Y/Z/W.
            x, y, z, w = param.data
            if len(inputs) == 1:
                inputs[0].default_value = (x,y,z,w)
            elif len(inputs) == 2:
                inputs[0].default_value = (x,y,z,1)
                inputs[1].default_value = w
            elif len(inputs) == 4:
                inputs[0].default_value = x
                inputs[1].default_value = y
                inputs[2].default_value = z
                inputs[3].default_value = w

            if param_name == 'CustomVector47':
                node_group_node.inputs['use_custom_vector_47'].default_value = 1.0

    links.new(material_output_node.inputs[0], node_group_node.outputs[0])

    # Add image texture nodes
    node_count = 0

    for texture_param in entry.textures:
        enable_inputs(node_group_node, texture_param.param_id.name)

        texture_node = nodes.new('ShaderNodeTexImage')
        texture_node.location = (-800, -500 * node_count + 1000)
        texture_file_name = texture_param.data
        texture_node.name = texture_file_name
        texture_node.label = texture_file_name
        texture_node.image = texture_name_to_image_dict[texture_file_name]
        matched_rgb_input = None
        matched_alpha_input = None
        for input in node_group_node.inputs:
            if texture_param.param_id.name == input.name.split(' ')[0]:
                if 'RGB' == input.name.split(' ')[1]:
                    matched_rgb_input = input
                else:
                    matched_alpha_input = input
        # For now, manually set the colorspace types....
        linear_textures = ['Texture6', 'Texture4']
        if texture_param.param_id.name in linear_textures:
            texture_node.image.colorspace_settings.name = 'Linear'
            texture_node.image.alpha_mode = 'CHANNEL_PACKED'
        
        uv_map_node = nodes.new('ShaderNodeUVMap')
        uv_map_node.name = 'uv_map_node'
        uv_map_node.location = (texture_node.location[0] - 900, texture_node.location[1])
        uv_map_node.label = texture_param.param_id.name + ' UV Map'

        if texture_param.param_id.name == 'Texture9':
            uv_map_node.uv_map = 'bake1'
        elif texture_param.param_id.name == 'Texture1':
            uv_map_node.uv_map = 'uvSet'
        else:
            uv_map_node.uv_map = 'map1'

        # Create Sampler Node
        sampler_node = nodes.new('CustomNodeUltimateSampler')
        sampler_node.name = 'sampler_node'
        sampler_node.label = 'Sampler' + texture_param.param_id.name.split('Texture')[1]
        sampler_node.location = (texture_node.location[0] - 600, texture_node.location[1])
        sampler_node.width = 500

        # TODO: Handle the None case?
        sampler_entry = None
        for sampler_param in entry.samplers:
            if texture_param.param_id.name.split('Texture')[1] == sampler_param.param_id.name.split('Sampler')[1]:
                sampler_entry = sampler_param
                break

        enable_inputs(node_group_node, sampler_entry.param_id.name)
        sampler_data = sampler_entry.data
        sampler_node.wrap_s = sampler_data.wraps.name
        sampler_node.wrap_t = sampler_data.wrapt.name
        sampler_node.wrap_r = sampler_data.wrapr.name
        sampler_node.min_filter = sampler_data.min_filter.name
        sampler_node.mag_filter = sampler_data.mag_filter.name
        sampler_node.anisotropic_filtering = sampler_data.max_anisotropy is not None
        sampler_node.max_anisotropy = sampler_data.max_anisotropy.name if sampler_data.max_anisotropy else 'One'
        sampler_node.border_color = tuple(sampler_data.border_color)
        sampler_node.lod_bias = sampler_data.lod_bias       

        links.new(sampler_node.inputs['UV Input'], uv_map_node.outputs[0])
        links.new(texture_node.inputs[0], sampler_node.outputs[0])
        links.new(matched_rgb_input, texture_node.outputs['Color'])
        links.new(matched_alpha_input, texture_node.outputs['Alpha'])
        node_count = node_count + 1

    # Set up color sets.
    # Use the default values for non required attributes to be consistent between renderers.
    # Ignore the rendering accuracy of missing required attributes for now.
    required_attributes = get_vertex_attributes(node_group_node, shader_name)

    def create_and_enable_color_set(name, row):
        enable_inputs(node_group_node, name)

        color_set_node = nodes.new('ShaderNodeVertexColor')
        color_set_node.name = name
        color_set_node.label = name
        color_set_node.layer_name = name
        # Vertically stack color sets with even spacing.
        color_set_node.location = (-500, 150 - row * 150)

        links.new(node_group_node.inputs[f'{name} RGB'], color_set_node.outputs['Color'])
        links.new(node_group_node.inputs[f'{name} Alpha'], color_set_node.outputs['Alpha'])

    if 'colorSet1' in required_attributes:
        create_and_enable_color_set('colorSet1', 0)

    if 'colorSet5' in required_attributes:
        create_and_enable_color_set('colorSet5', 1)

def read_nuhlpb_json(nuhlpb_path) -> str:
    import subprocess
    ssbh_lib_json_exe_path = get_ssbh_lib_json_exe_path()
    output_json_path = nuhlpb_path + '.json'
    try:
        subprocess.run([ssbh_lib_json_exe_path, nuhlpb_path, output_json_path], capture_output=True, check=True)
    except:
        pass # Lol
    
    nuhlpb_json = None
    with open(output_json_path) as f:
        nuhlpb_json = json.load(f)
    return nuhlpb_json

def create_new_empty(name, parent, specified_collection=None) -> bpy.types.Object:
    empty = bpy.data.objects.new('empty', None)
    empty.name = name

    if specified_collection is None:
        bpy.context.collection.objects.link(empty)
    else:
        specified_collection.objects.link(empty)
    empty.parent = parent
    return empty

def get_from_mesh_list_with_pruned_name(meshes:list, pruned_name:str, fallback=None) -> bpy.types.Object:
    for mesh in meshes:
        if mesh.name.startswith(pruned_name):
            return mesh
    return fallback

def copy_empty(original:bpy.types.Object, specified_collection=None) -> bpy.types.Object:
    copy = original.copy()
    if specified_collection is None:
        bpy.context.collection.objects.link(copy)
    else:
        specified_collection.objects.link(copy)
    return copy

def import_nuhlpb_data_from_json(nuhlpb_json, armature, context):
    '''
    The nuhlpb data will be stored in a tree of empty objects.
    '''
    root_empty = create_new_empty('_NUHLPB', armature)
    root_empty['major_version'] = nuhlpb_json['data']['Hlpb']['major_version']
    root_empty['minor_version'] = nuhlpb_json['data']['Hlpb']['minor_version']
    aim_entries_empty = create_new_empty('aim_entries', root_empty)
    for aim_entry in nuhlpb_json['data']['Hlpb']['aim_entries']:
        aim_entry_empty = create_new_empty(aim_entry['name'], aim_entries_empty)
        aim_entry_empty['aim_bone_name1'] = aim_entry['aim_bone_name1']
        aim_entry_empty['aim_bone_name2'] = aim_entry['aim_bone_name2'] 
        aim_entry_empty['aim_type1'] = aim_entry['aim_type1']
        aim_entry_empty['aim_type2'] = aim_entry['aim_type2']
        aim_entry_empty['target_bone_name1'] = aim_entry['target_bone_name1'] 
        aim_entry_empty['target_bone_name2'] = aim_entry['target_bone_name2']
        for unk_index in range(1, 22+1):
            aim_entry_empty[f'unk{unk_index}'] = aim_entry[f'unk{unk_index}']
        create_aim_type_helper_bone_constraints(aim_entry['name'], armature, aim_entry['target_bone_name1'], aim_entry['aim_bone_name1'])
          
    interpolation_entries_empty = create_new_empty('interpolation_entries', root_empty)
    for interpolation_entry in nuhlpb_json['data']['Hlpb']['interpolation_entries']:
        ie = interpolation_entry
        ie_empty = create_new_empty(ie['name'], interpolation_entries_empty)
        ie_empty['bone_name'] = ie['bone_name']
        ie_empty['root_bone_name'] = ie['root_bone_name']
        ie_empty['parent_bone_name'] = ie['parent_bone_name']
        ie_empty['driver_bone_name'] = ie['driver_bone_name']
        ie_empty['unk_type'] = ie['unk_type']
        aoi = ie['aoi']
        ie_empty['aoi'] = [aoi['x'], aoi['y'], aoi['z']]
        quat1 = ie['quat1']
        ie_empty['quat1'] = [quat1['x'],quat1['y'],quat1['z'],quat1['w']]
        quat2 = ie['quat2']
        ie_empty['quat2'] = [quat2['x'],quat2['y'],quat2['z'],quat2['w']]
        range_min = ie['range_min']
        ie_empty['range_min'] = [range_min['x'], range_min['y'], range_min['z']]
        range_max = ie['range_max']
        ie_empty['range_max'] = [range_max['x'], range_max['y'], range_max['z']]
        create_interpolation_type_helper_bone_constraints(
            ie['name'], armature,
            ie['driver_bone_name'], ie['parent_bone_name'],
            [aoi['y'], aoi['x'], aoi['z']]
        )
    '''
    list_one and list_two can be inferred from the aim and interpolation entries, so no need to track
    '''


def create_aim_type_helper_bone_constraints(constraint_name, armature, owner_bone_name, target_bone_name):
    bpy.ops.object.mode_set(mode='POSE', toggle=False)
    #print(f'{constraint_name}, {armature}, {owner_bone_name}, {target_bone_name}')
    owner_bone = armature.pose.bones.get(owner_bone_name, None)
    if owner_bone is not None:
        new_constraint = owner_bone.constraints.new('DAMPED_TRACK')
        new_constraint.name = constraint_name
        new_constraint.track_axis = 'TRACK_Y'
        new_constraint.influence = 1.0
        new_constraint.target = armature
        new_constraint.subtarget = target_bone_name
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


def create_interpolation_type_helper_bone_constraints(constraint_name, armature, owner_bone_name, target_bone_name, aoi_xyz_list):
    bpy.ops.object.mode_set(mode='POSE', toggle=False)
    owner_bone = armature.pose.bones.get(owner_bone_name, None)
    if owner_bone is not None:
        x,y,z = 'X', 'Y', 'Z'
        for index, axis in enumerate([x,y,z]):
            crc = owner_bone.constraints.new('COPY_ROTATION')
            crc.name = f'{constraint_name}.{axis}'
            crc.target = armature
            crc.subtarget =  target_bone_name
            crc.target_space = 'POSE'
            crc.owner_space = 'POSE'
            crc.use_x = True if axis is x else False
            crc.use_y = True if axis is y else False
            crc.use_z = True if axis is z else False
            crc.influence = aoi_xyz_list[index]
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)