import numpy as np
import cv2
import moderngl
from alfr.globals import ContextManager
from alfr.camera import Camera
from pyrr import Matrix44, Quaternion, Vector3, vector
import json
import os
from typing import Union


def load_shots_from_json(
    json_file: str,
    fovy: float = 60.0,
    ctx: moderngl.Context = ContextManager.get_default_context(),
):
    """
    Loads shots from a json file.
    """
    shots = []
    with open(json_file, "r") as f:
        data = json.load(f)

        json_dir = os.path.dirname(os.path.realpath(f.name))

        if "images" in data.keys():
            for image in data["images"]:
                file, pos, rot, fov = get_file_pos_rot(image)
                shot = Shot(
                    os.path.join(json_dir, file),
                    Vector3(pos),
                    Quaternion(rot),
                    fov if fov is not None else fovy,
                    shot_aspect_ratio=1.0,
                    ctx=ctx,
                )
                shots.append(shot)

    return shots


def get_from_dict(d: dict, keys: list):
    for key in keys:
        if key in d.keys():
            return d[key]
    return None


def get_file_pos_rot(images: dict):
    file = get_from_dict(images, ["imagefile", "file", "image"])
    pos = get_from_dict(images, ["location", "pos", "loc"])
    rot = get_from_dict(images, ["rotation", "rot", "quaternion"])
    fov = get_from_dict(images, ["fovy", "fov", "fieldofview"])

    if file is None or pos is None or rot is None:
        raise Exception("Not all keys found in images dict!")

    return file, pos, rot, fov


class Shot(Camera):
    """One perspective of the light field"""

    def __init__(
        self,
        shot_filename: Union[str, np.ndarray],
        shot_position: Vector3,
        shot_rotation: Quaternion,
        shot_fovy_degrees: float = 60.0,
        shot_aspect_ratio: float = 1.0,
        ctx: moderngl.Context = ContextManager.get_default_context(),
    ):
        super().__init__(
            field_of_view_degrees=shot_fovy_degrees,
            ratio=shot_aspect_ratio,
            position=shot_position,
            quaternion=shot_rotation,
        )

        # global g.ctx
        if ctx is None:
            raise RuntimeError("No OpenGL context available!")

        # one perspective of the light field
        # self.texture = window.load_texture_2d(shot_filename)

        if isinstance(shot_filename, str):
            img = self._load_image(shot_filename)
        elif isinstance(shot_filename, np.ndarray):
            img = shot_filename
        else:
            raise Exception("Unknown type for {shot_filename}")
        self.texture = ctx.texture(img.shape[1::-1], img.shape[2], img)

    def _load_image(self, texture_filename) -> np.ndarray:
        img = cv2.imread(texture_filename)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # convert to RGB, opencv uses BGR
        img = np.flip(img, 0).copy(order="C")  # flip image vertically
        return img

    def use(self, renderer):
        """
        Use this perspective of the light field.
        """
        self.texture.use(0)

        # get uniforms from shader program
        self.shotViewMat = renderer.program["shotViewMatrix"]
        self.shotProjMat = renderer.program["shotProjectionMatrix"]

        self.shotProjMat.write(self.projection_matrix.astype("f4"))
        self.shotViewMat.write(self.view_matrix.astype("f4"))
