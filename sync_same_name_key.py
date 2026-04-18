bl_info = {
    "name": "Same Name ShapeKey Sync",
    "author": "ranhai613",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > MyAddon Tab",
    "description": "Sync shape key values across all objects in the scene that have shape keys with the same name.",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
from bpy.props import StringProperty, FloatProperty, CollectionProperty, IntProperty, BoolProperty
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

    # Skip expensive sync while keys are being added in bulk.
    if getattr(scene, "sync_keys_bulk_updating", False):
        return

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

# -----------------------
# UI
# -----------------------
class VIEW3D_PT_multi_sync(bpy.types.Panel):
    bl_label = "Same Name ShapeKey Sync"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MyAddon"

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
# Operators
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

        # Collect first-seen value for each key name once to avoid repeated full-scene scans.
        first_value_by_name = {}
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or not obj.data.shape_keys:
                continue
            for key in obj.data.shape_keys.key_blocks:
                if key.name == "Basis" or key.name in first_value_by_name:
                    continue
                first_value_by_name[key.name] = key.value

        scene.sync_keys_bulk_updating = True
        try:
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
                    item.value = first_value_by_name.get(key.name, key.value)

                    existing_names.add(key.name)
        finally:
            scene.sync_keys_bulk_updating = False

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
    bpy.types.Scene.sync_keys_bulk_updating = BoolProperty(default=False)

def unregister():
    del bpy.types.Scene.sync_keys_bulk_updating
    del bpy.types.Scene.sync_keys
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()