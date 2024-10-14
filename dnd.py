import bpy
from . import fn

def get_dndsupport():
    return bpy.context.preferences.addons[__package__].preferences.dnd

def get_namingmode():
    return bpy.context.preferences.addons[__package__].preferences.naming

def get_dndintensity():
    return bpy.context.preferences.addons[__package__].preferences.dnd_intensity

class OBJECT_OT_drag_drop_detect(bpy.types.Operator):
    bl_idname = "object.drag_drop_detect"
    bl_label = "Drag and Drop Detector"
    _timer = None
    _in_drag_drop = False

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and self._in_drag_drop:
            # Reset flag and stop checking
            self._in_drag_drop = False
            bpy.app.timers.unregister(self._timer)
            # Reinvoke the operator to reset state
            bpy.ops.object.drag_drop_detect('INVOKE_DEFAULT')
            return {'FINISHED'}
        
        if event.type == 'TIMER':
            for obj in context.scene.objects:
                if obj.type == 'EMPTY' and obj.empty_display_type == 'IMAGE' and not obj.get('drag_processed', False):
                    obj['drag_processed'] = True
                    dndhandler(obj, context, self)
                    return {'RUNNING_MODAL'}

        if event.type == 'DRAGDROP':
            self._in_drag_drop = True
        
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

def dndhandler(obj, context, detector):
    # Your custom method logic here
    print("Drag and drop event triggered.")
    if (get_dndsupport()):
        fn.convert_empty_image_to_mesh(
                context, 
                obj,
                "IMAGE",
                True,
                1.0) #get_dndintensity()