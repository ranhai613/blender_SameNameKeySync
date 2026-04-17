bl_info = {
    "name": "Same Name ShapeKey Sync",
    "blender": (3, 0, 0),
    "category": "Object",
}

import bpy
from bpy.props import StringProperty, FloatProperty, CollectionProperty, IntProperty
from bpy.types import PropertyGroup

# -----------------------
# Property group (manages one key)
# -----------------------
class SyncKeyItem(PropertyGroup):
    name: StringProperty(name="Key Name")
    value: FloatProperty(
        name="Value",
        min=0.0, max=1.0,
        update=lambda self, context: update_sync_keys(context, self.name)
    )

# -----------------------
# Sync processing (all objects in the scene)
# -----------------------
def update_sync_keys(context, updated_key_name):
    scene = context.scene
    for item in scene.sync_keys:
        key_name = item.name
        value = item.value

        if not key_name:
            continue

        for obj in bpy.data.objects:  # all objects in the scene
            if obj.type != 'MESH' or not obj.data.shape_keys:
                continue
            keys = obj.data.shape_keys.key_blocks
            if key_name in keys:
                keys[key_name].value = value
                obj.active_shape_key_index = keys.find(updated_key_name)
        
        # try to update the ref object if it exists
        if key_name.startswith('===') and key_name.endswith('==='):
            continue
        
        if not '__' in key_name:
            continue
        
        name_prefix = key_name.split('__')[0]
        ref_col = bpy.data.collections.get(name_prefix)
        if not ref_col:
            continue
        
        key_name_without_prefix = key_name[len(name_prefix)+2:]
        for ref_obj in ref_col.objects:
            if ref_obj.type != 'MESH' or not ref_obj.data.shape_keys:
                continue
            keys = ref_obj.data.shape_keys.key_blocks
            if key_name_without_prefix in keys:
                keys[key_name_without_prefix].value = value
        

# -----------------------
# UI
# -----------------------
class VIEW3D_PT_multi_sync(bpy.types.Panel):
    bl_label = "Multi ShapeKey Sync"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.operator("sync_keys.add_key", text="Add Key")
        row.operator("sync_keys.add_all_keys", text="Add All Keys from Selected")
        row.operator("sync_keys.clear_all_keys", text="Clear All")

        for idx, item in enumerate(scene.sync_keys):
            box = layout.box()
            row = box.row(align=True)
            row.prop(item, "name", text="", text_ctxt="Key Name")
            row.prop(item, "value", text="")
            row.operator("sync_keys.remove_key", text="", icon='X').index = idx

# -----------------------
# オペレーター
# -----------------------
class SYNCKEYS_OT_add_key(bpy.types.Operator):
    bl_idname = "sync_keys.add_key"
    bl_label = "Add Sync Key"

    def execute(self, context):
        context.scene.sync_keys.add()
        return {'FINISHED'}

class SYNCKEYS_OT_remove_key(bpy.types.Operator):
    bl_idname = "sync_keys.remove_key"
    bl_label = "Remove Sync Key"

    index: IntProperty()

    def execute(self, context):
        context.scene.sync_keys.remove(self.index)
        return {'FINISHED'}

class SYNCKEYS_OT_add_all_keys(bpy.types.Operator):
    bl_idname = "sync_keys.add_all_keys"
    bl_label = "Add All Keys from Selected"

    def execute(self, context):
        scene = context.scene
        existing_names = {item.name for item in scene.sync_keys}

        for obj in context.selected_objects:
            if obj.type != 'MESH' or not obj.data.shape_keys:
                continue
            for key in obj.data.shape_keys.key_blocks:
                if key.name == "Basis":
                    continue
                if key.name in existing_names:
                    continue

                # Add a new item
                item = scene.sync_keys.add()
                item.name = key.name

                # Read value from all objects (use the first found value as the initial)
                initial_value = key.value
                for obj2 in bpy.data.objects:
                    if obj2.type != 'MESH' or not obj2.data.shape_keys:
                        continue
                    keys2 = obj2.data.shape_keys.key_blocks
                    if key.name in keys2:
                        initial_value = keys2[key.name].value
                        break
                item.value = initial_value

                existing_names.add(key.name)

        return {'FINISHED'}

class SYNCKEYS_OT_clear_all_keys(bpy.types.Operator):
    bl_idname = "sync_keys.clear_all_keys"
    bl_label = "Clear All Keys"

    def execute(self, context):
        context.scene.sync_keys.clear()
        return {'FINISHED'}

# -----------------------
# Register
# -----------------------
classes = [
    SyncKeyItem,
    VIEW3D_PT_multi_sync,
    SYNCKEYS_OT_add_key,
    SYNCKEYS_OT_remove_key,
    SYNCKEYS_OT_add_all_keys,
    SYNCKEYS_OT_clear_all_keys,
]

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.sync_keys = CollectionProperty(type=SyncKeyItem)

def unregister():
    del bpy.types.Scene.sync_keys
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()