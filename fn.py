import bpy, re
from mathutils import Vector



# import importlib
# iap = importlib.import_module('io_import_images_as_planes')

## //--- Function are taken from Import image as plane addon (with some tweaks)
## credits to Florian Meyer (tstscr), mont29, matali, Ted Schundler (SpkyElctrc)

from collections import namedtuple
ImageSpec = namedtuple(
    'ImageSpec',
    ['image', 'size', 'frame_start', 'frame_offset', 'frame_duration'])

def get_prefs():
    '''
    function to read current addon preferences properties
    access with : get_prefs().super_special_option
    '''
    return bpy.context.preferences.addons[__package__].preferences

def clean_node_tree(node_tree):
    """Clear all nodes in a shader node tree except the output.

    Returns the output node
    """
    nodes = node_tree.nodes
    for node in list(nodes):  # copy to avoid altering the loop's data source
        if not node.type == 'OUTPUT_MATERIAL':
            nodes.remove(node)

    return node_tree.nodes[0]

#### /// can load from IAP
def get_input_nodes(node, links):
    """Get nodes that are a inputs to the given node"""
    # Get all links going to node.
    input_links = {lnk for lnk in links if lnk.to_node == node}
    # Sort those links, get their input nodes (and avoid doubles!).
    sorted_nodes = []
    done_nodes = set()
    for socket in node.inputs:
        done_links = set()
        for link in input_links:
            nd = link.from_node
            if nd in done_nodes:
                # Node already treated!
                done_links.add(link)
            elif link.to_socket == socket:
                sorted_nodes.append(nd)
                done_links.add(link)
                done_nodes.add(nd)
        input_links -= done_links
    return sorted_nodes


def auto_align_nodes(node_tree):
    """Given a shader node tree, arrange nodes neatly relative to the output node."""
    x_gap = 200
    y_gap = 180
    nodes = node_tree.nodes
    links = node_tree.links
    output_node = None
    for node in nodes:
        if node.type == 'OUTPUT_MATERIAL' or node.type == 'GROUP_OUTPUT':
            output_node = node
            break

    else:  # Just in case there is no output
        return

    def align(to_node):
        from_nodes = get_input_nodes(to_node, links)
        for i, node in enumerate(from_nodes):
            node.location.x = min(node.location.x, to_node.location.x - x_gap)
            node.location.y = to_node.location.y
            node.location.y -= i * y_gap
            node.location.y += (len(from_nodes) - 1) * y_gap / (len(from_nodes))
            align(node)

    align(output_node)


#### above func can be loaded from IAP via import  (below are modified) ///

def apply_texture_options(texture, img_spec):
        image_user = texture.image_user
        # image_user.use_auto_refresh = True # self.use_auto_refresh
        image_user.frame_start = img_spec.frame_start
        image_user.frame_offset = img_spec.frame_offset
        image_user.frame_duration = img_spec.frame_duration

        # Image sequences need auto refresh to display reliably
        # if img_spec.image.source == 'SEQUENCE':
        if img_spec.image.source in {'SEQUENCE', 'MOVIE'}:
            image_user.use_auto_refresh = True

        texture.extension = 'CLIP'  # Default of "Repeat" can cause artifacts

def create_cycles_texnode(context, node_tree, img_spec):
        tex_image = node_tree.nodes.new('ShaderNodeTexImage')
        tex_image.image = img_spec.image
        tex_image.show_texture = True
        apply_texture_options(tex_image, img_spec)
        return tex_image

def create_cycles_material(context, img_spec, intensity, overwrite_material=True, use_transparency=True):
    image = img_spec.image
    name_compat = bpy.path.display_name_from_filepath(image.filepath)
    material = None
    
    if overwrite_material:
        material = bpy.data.materials.get(name_compat)
    if not material:
        material = bpy.data.materials.new(name=name_compat)
    
    material.use_nodes = True
    
    if use_transparency:
        material.blend_method = 'BLEND'
    
    node_tree = material.node_tree
    out_node = clean_node_tree(node_tree)
    tex_image = create_cycles_texnode(context, node_tree, img_spec)
    core_shader = node_tree.nodes.new('ShaderNodeEmission')
    core_shader.inputs['Strength'].default_value = intensity
    core_shader.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    node_tree.links.new(core_shader.inputs['Color'], tex_image.outputs['Color'])
    node_tree.links.new(out_node.inputs['Surface'], core_shader.outputs[0])
    auto_align_nodes(node_tree)
    return material


 ## Import image as plane addon function ---//


def create_image_plane(coords, name):
    '''Create an a mesh plane with a defaut UVmap from passed coordinate
    object and mesh get passed name
    
    return plane object
    '''
    fac = [(0, 1, 3, 2)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(coords, [], fac)
    plane = bpy.data.objects.new(name, me)
    # col = bpy.context.collection
    # col.objects.link(plane)

    me.uv_layers.new(name='UVMap')
    return plane


def get_ref_object_space_coord(o):
    size = o.empty_display_size
    x,y = o.empty_image_offset
    img = o.data

    res_x, res_y = img.size
    scaling = 1 / max(res_x, res_y)

    # 3----2
    # |    |
    # 0----1 

    corners = [
        Vector((0,0)),
        Vector((res_x, 0)),
        Vector((0, res_y)),
        Vector((res_x, res_y)),
        ]

    obj_space_corners = []
    for co in corners:
        nco_x = ((co.x + (x * res_x)) * size) * scaling
        nco_y = ((co.y + (y * res_y)) * size) * scaling
        obj_space_corners.append(Vector((nco_x, nco_y, 0)))
    return obj_space_corners

def convert_empty_image_to_mesh(context, o, name_from='IMAGE', delete_ref=True, intensity=1.0):
    """shader in ['EMISSION', 'PRINCIPLED', 'SHADELESS']"""
    img = o.data
    img_user = o.image_user
    col = o.users_collection[0]

    if name_from == 'IMAGE':
        name = bpy.path.display_name_from_filepath(img.name)
    if name_from == 'OBJECT':
        name = re.sub(r'\.\d{3}$', '', o.name) + '_texplane'
        ## increment if needed (if omitted, blender will do it)
    new_name = name
    i = 0
    while new_name in [ob.name for ob in col.all_objects]:
        i += 1
        new_name = f'{name}.{i:03d}'
    name = new_name

    print(f'\nConvert ref to mesh: {o.name} -> {name}')
    obj_space_corners = get_ref_object_space_coord(o)
    plane = create_image_plane(obj_space_corners, name=name)
    # link in same collection
    col.objects.link(plane)

    ## img_spec :: 'image', 'size', 'frame_start', 'frame_offset', 'frame_duration'
    img_spec = ImageSpec(img, (img.size[0], img.size[1]), img_user.frame_start, img_user.frame_offset, img_user.frame_duration)
    material = create_cycles_material(context, img_spec, intensity)
    plane.data.materials.append(material)
    plane.parent = o.parent
    plane.matrix_local = o.matrix_local
    plane.matrix_parent_inverse = o.matrix_parent_inverse

    if delete_ref:
        bpy.data.objects.remove(o)
