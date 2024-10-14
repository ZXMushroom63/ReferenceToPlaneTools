bl_info = {
    "name": "Reference Image to Plane Tools",
    "description": "Convert reference images to planes, with drag and drop autoconversion support.",
    "author": "ZXMushroom63",
    "version": (0, 0, 1),
    "blender": (4, 2, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object" }


import bpy
from bpy.types import Operator
from bpy.props import FloatVectorProperty, BoolProperty, FloatProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
from . import fn
from . import dnd

def get_namingmode():
    return bpy.context.preferences.addons[__package__].preferences.naming

class RTP_OT_add_object(Operator, AddObjectHelper):
    """Convert to a plane"""
    bl_idname = "reference_to_plane.convert_to_plane"
    bl_label = "Convert to Plane"
    bl_description = "Convert selected reference images to textured plane"
    bl_options = {'REGISTER', 'UNDO'}
    
    del_ref: bpy.props.BoolProperty(name="Delete Reference Object", default=True, description="Delete empty image object reference once texture plane is created")

    # intensity_ref: bpy.props.FloatProperty(
    #         name="Intensity",
    #         default=1.0,
    #         min=0.0,
    #         max=100.0,
    #         subtype='FACTOR',
    #         description="Emissive shader intensity",
    #         update=None
    #         )
    
    @classmethod
    def poll(cls, context):
        return True

    @staticmethod
    def _is_ref(o):
        return o and o.type == 'EMPTY' and o.empty_display_type == 'IMAGE' and o.data

    def execute(self, context):
        pool = [o for o in context.selected_objects]
        if context.object and context.object not in pool:
            pool.append(context.object)
        converted = 0

        for o in pool:
            if not self._is_ref(o):
                continue
            fn.convert_empty_image_to_mesh(
                context, 
                o, 
                get_namingmode(), 
                self.del_ref,
                1.0) #self.intensity_ref
            
            converted += 1

        if not converted:
            self.report({'ERROR'}, 'Nothing converted')
            return {"CANCELLED"}

        self.report({'INFO'}, f'{converted} converted to mesh plane')
        return {"FINISHED"}


# Registration
def add_convert_button(self, context):
    self.layout.operator(
        RTP_OT_add_object.bl_idname,
        text="Convert Reference To Plane",
        icon='PLUGIN')

class RITPPrefs(bpy.types.AddonPreferences):
    bl_idname = __name__

    # Define properties
    dnd: bpy.props.BoolProperty(
        name="Drag and Drop Support",
        description="Replace drag-and-dropped reference images with planes.",
        default=False
    )
    
    # dnd_intensity: bpy.props.FloatProperty(
    #     name="DnD Emission Intensity",
    #     description="The intensity/emission strength of the shader when using drag and drop.",
    #     default=1.0
    # )
    
    naming: bpy.props.EnumProperty(name="Naming Convention", 
        items=(
                ('OBJECT',"Object Name","Name generated planes after the original empties."),
                ('IMAGE', "Image Filename", "Name generated planes after the image filename of the empty.")
            ), 
        default='OBJECT',
        description="Naming convention for manual conversions.")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reference Image To Plane Preferences")
        layout.prop(self, "dnd")
        layout.prop(self, "dnd_intensity")
        layout.prop(self, "naming")

#DND stuff
def reference_image_created(scene):
    for obj in scene.objects:
        if obj.type == 'EMPTY' and obj.empty_display_type == 'IMAGE':
            # Run your method on the reference image empty
            print(f'Reference image created: {obj.name}')

def register():
    bpy.utils.register_class(RTP_OT_add_object)
    bpy.utils.register_class(RITPPrefs)
    bpy.types.VIEW3D_MT_object.append(add_convert_button)
    bpy.utils.register_class(dnd.OBJECT_OT_drag_drop_detect)
    bpy.app.timers.register(lambda: bpy.ops.object.drag_drop_detect('INVOKE_DEFAULT'), first_interval=0.1)

def unregister():
    bpy.utils.unregister_class(RTP_OT_add_object)
    bpy.utils.unregister_class(RITPPrefs)
    bpy.types.VIEW3D_MT_object.remove(add_convert_button)
    bpy.utils.unregister_class(dnd.OBJECT_OT_drag_drop_detect)


if __name__ == "__main__":
    register()