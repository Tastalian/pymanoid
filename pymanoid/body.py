#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Stephane Caron <stephane.caron@normalesup.org>
#
# This file is part of pymanoid <https://github.com/stephane-caron/pymanoid>.
#
# pymanoid is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pymanoid is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# pymanoid. If not, see <http://www.gnu.org/licenses/>.

import openravepy

from numpy import array, dot, zeros

from rotations import crossmat, rotation_matrix_from_rpy, rpy_from_quat
from sim import get_openrave_env


class Body(object):

    count = 0  # counter for anonymous bodies

    """
    Wrapper around OpenRAVE KinBody.
    """

    def __init__(self, kinbody, pos=None, rpy=None, pose=None, color=None,
                 visible=True, transparency=None, name=None):
        """
        Create body from an OpenRAVE KinBody.

        INPUT:

        - ``kinbody`` -- KinBody object to wrap
        - ``pos`` -- (optional) initial position in inertial frame
        - ``rpy`` -- (optional) initial orientation in inertial frame
        - ``pose`` -- (optional) initial pose, supersedes ``pos`` and ``rpy``
        - ``color`` -- (optional) color applied to all links of the KinBody
        - ``visible`` -- (optional) initial visibility
        - ``transparency`` -- (optional) from 0 for opaque to 1 for invisible
        - ``name`` -- (optional) body name in OpenRAVE scope
        """
        if not kinbody.GetName():
            if name is None:
                name = "%s%s" % (type(self).__name__, Body.count)
                Body.count += 1
            kinbody.SetName(name)
        self.rave = kinbody
        if pos is not None:
            self.set_pos(pos)
        if rpy is not None:
            self.set_rpy(rpy)
        if pose is not None:
            self.set_pose(pose)
        if color is not None:
            self.set_color(color)
        if not visible:
            self.set_visible(False)
        if transparency is not None:
            self.set_transparency(transparency)
        self.is_visible = visible

    def __str__(self):
        return "pymanoid.Body('%s')" % self.name

    def set_color(self, color):
        """
        Set the color of all bodies in the OpenRAVE KinBody object.

        INPUT:

        - ``color`` -- color code in Matplotlib convention,
                       see <http://matplotlib.org/api/colors_api.html>.
        """
        if color == 'w':
            acolor = array([1., 1., 1.])
            dcolor = array([1., 1., 1.])
        else:  # add other colors above black
            acolor = array([.2, .2, .2])
            dcolor = array([.2, .2, .2])
            rgb, cmy = ['r', 'g', 'b'], ['c', 'm', 'y']
            if color in rgb:
                cdim = rgb.index(color)
                acolor[cdim] += .2
                dcolor[cdim] += .4
            elif color in cmy:
                cdim = cmy.index(color)
                acolor[(cdim + 1) % 3] += .2
                acolor[(cdim + 2) % 3] += .2
                dcolor[(cdim + 1) % 3] += .4
                dcolor[(cdim + 2) % 3] += .4
        for link in self.rave.GetLinks():
            for g in link.GetGeometries():
                g.SetAmbientColor(acolor)
                g.SetDiffuseColor(dcolor)

    def set_transparency(self, transparency):
        for link in self.rave.GetLinks():
            for geom in link.GetGeometries():
                geom.SetTransparency(transparency)

    def show(self):
        self.rave.SetVisible(True)

    def hide(self):
        self.rave.SetVisible(False)

    def set_visible(self, visible):
        self.is_visible = visible
        self.rave.SetVisible(visible)

    @property
    def index(self):
        """Notably used to compute jacobians and hessians."""
        return self.rave.GetIndex()

    @property
    def name(self):
        """Get name from OpenRAVE object."""
        return self.rave.GetName()

    @property
    def T(self):
        """Transformation matrix."""
        return self.rave.GetTransform()

    @property
    def pose(self):
        """Pose (in OpenRAVE convention)."""
        pose = self.rave.GetTransformPose()
        if pose[0] < 0:  # convention: cos(alpha) > 0
            # this convention enforces Slerp shortest path
            pose[:4] *= -1
        return pose

    @property
    def R(self):
        """Rotation matrix"""
        return self.T[0:3, 0:3]

    @property
    def p(self):
        """Position in world frame"""
        return self.T[0:3, 3]

    @property
    def x(self):
        return self.p[0]

    @property
    def y(self):
        return self.p[1]

    @property
    def z(self):
        return self.p[2]

    @property
    def t(self):
        """Tangent vector"""
        return self.T[0:3, 0]

    @property
    def b(self):
        """Binormal vector"""
        return self.T[0:3, 1]

    @property
    def n(self):
        """Normal vector"""
        return self.T[0:3, 2]

    @property
    def quat(self):
        return self.pose[0:4]

    @property
    def rpy(self):
        """Roll-pitch-yaw angles"""
        return rpy_from_quat(self.quat)

    @property
    def roll(self):
        return self.rpy[0]

    @property
    def pitch(self):
        return self.rpy[1]

    @property
    def yaw(self):
        return self.rpy[2]

    def set_transform(self, T):
        self.rave.SetTransform(T)

    def set_pos(self, pos):
        T = self.T.copy()
        T[:3, 3] = pos
        self.set_transform(T)

    def set_rotation_matrix(self, R):
        T = self.T.copy()
        T[:3, :3] = R
        self.set_transform(T)

    def set_x(self, x):
        T = self.T.copy()
        T[0, 3] = x
        self.set_transform(T)

    def set_y(self, y):
        T = self.T.copy()
        T[1, 3] = y
        self.set_transform(T)

    def set_z(self, z):
        T = self.T.copy()
        T[2, 3] = z
        self.set_transform(T)

    def set_rpy(self, rpy):
        T = self.T.copy()
        T[0:3, 0:3] = rotation_matrix_from_rpy(*rpy)
        self.set_transform(T)

    def set_roll(self, roll):
        return self.set_rpy([roll, self.pitch, self.yaw])

    def set_pitch(self, pitch):
        return self.set_rpy([self.roll, pitch, self.yaw])

    def set_yaw(self, yaw):
        return self.set_rpy([self.roll, self.pitch, yaw])

    def set_pose(self, pose):
        T = openravepy.matrixFromPose(pose)
        self.set_transform(T)

    def set_quat(self, quat):
        pose = self.pose.copy()
        pose[0:4] = quat
        self.set_pose(pose)

    def remove(self):
        """Remove body from OpenRAVE environment."""
        env = get_openrave_env()
        with env:
            env.Remove(self.rave)

    def __del__(self):
        """Add body removal to garbage collection step (effective)."""
        self.remove()

    def apply_twist(self, v, omega, dt):
        """
        Apply a twist [v, omega] defined in the local coordinate frame.

        INPUT:

        - ``v`` -- linear velocity in local frame
        - ``omega`` -- angular velocity in local frame
        - ``dt`` -- duration of twist application
        """
        self.set_pos(self.p + v * dt)
        self.set_rotation_matrix(self.R + dot(crossmat(omega), self.R) * dt)


class Box(Body):

    def __init__(self, X, Y, Z, pos=None, rpy=None, pose=None, color='r',
                 visible=True, transparency=None, name=None, dZ=0.):
        """
        Create a new rectangular box.

        INPUT:

        - ``X`` -- box half-length
        - ``Y`` -- box half-width
        - ``Z`` -- box half-height
        - ``pos`` -- initial position in inertial frame
        - ``rpy`` -- initial orientation in inertial frame
        - ``color`` -- color letter in ['r', 'g', 'b']
        - ``name`` -- object's name (optional)
        - ``pose`` -- initial pose (supersedes pos and rpy)
        - ``visible`` -- initial box visibility
        - ``transparency`` -- (optional) from 0 for opaque to 1 for invisible
        - ``dZ`` -- special value used to make Contact slabs
        """
        self.X = X
        self.Y = Y
        self.Z = Z
        aabb = [0., 0., dZ, X, Y, Z]
        env = get_openrave_env()
        with env:
            box = openravepy.RaveCreateKinBody(env, '')
            box.InitFromBoxes(array([array(aabb)]), True)
            super(Box, self).__init__(
                box, pos=pos, rpy=rpy, pose=pose, color=color, visible=visible,
                transparency=transparency, name=name)
            env.Add(box, True)


class Cube(Box):

    def __init__(self, size, pos=None, rpy=None, pose=None, color='r',
                 visible=True, transparency=None, name=None):
        """
        Create a new cube.

        INPUT:

        - ``size`` -- half-length of a side of the cube
        - ``pos`` -- initial position in inertial frame
        - ``rpy`` -- initial orientation in inertial frame
        - ``pose`` -- initial pose (supersedes pos and rpy)
        - ``color`` -- color in matplotlib format ('r', 'g', 'b', 'm', etc.)
        - ``visible`` -- initial box visibility
        - ``transparency`` -- (optional) from 0 for opaque to 1 for invisible
        - ``name`` -- object's name (optional)
        """
        super(Cube, self).__init__(
            size, size, size, pos=pos, rpy=rpy, color=color, name=name,
            pose=pose, visible=visible, transparency=transparency)


class Point(Cube):

    def __init__(self, pos=None, size=0.01, color='r', visible=True,
                 transparency=None, name=None):
        """
        Points are simply cubes with a default size.

        INPUT:

        - ``pos`` -- (optional) initial position in inertial frame
        - ``size`` -- (optional) cube size, defaults to 1 cm
        - ``color`` -- color in matplotlib format ('r', 'g', 'b', 'm', etc.)
        - ``visible`` -- initial box visibility
        - ``transparency`` -- (optional) from 0 for opaque to 1 for invisible
        - ``name`` -- object's name (optional)
        """
        if pos is None:
            pos = [0., 0., 0.]
        super(Point, self).__init__(
            size, pos=pos, color=color, visible=visible,
            transparency=transparency, name=name)
        self.__pd = zeros(3)

    @property
    def pd(self):
        return self.__pd.copy()

    def set_velocity(self, pd):
        """Update the point-mass velocity."""
        self.__pd = array(pd)

    def integrate_acceleration(self, pdd, dt):
        """
        Euler integration of constant acceleration ``pdd`` over duration ``dt``.

        INPUT:

        - ``pdd`` -- 3D acceleration vector
        - ``dt`` -- duration in [s]
        """
        self.set_pos(self.p + self.pd * dt + pdd * .5 * dt ** 2)
        self.set_velocity(self.pd + pdd * dt)


class PointMass(Point):

    def __init__(self, pos, mass, *args, **kwargs):
        """
        A point-mass is a simple cube with size proportional to its mass.

        INPUT:

        - ``pos`` -- initial position in inertial frame
        - ``mass`` -- total mass in [kg]
        """
        size = max(5e-3, 6e-4 * mass)
        super(PointMass, self).__init__(pos, size, *args, **kwargs)
        self.mass = mass


class Manipulator(Body):

    def __init__(self, rave_manipulator, color=None, pos=None, rpy=None,
                 pose=None, visible=True, transparency=None):
        super(Manipulator, self).__init__(
            rave_manipulator, color=color, pos=pos, rpy=rpy, pose=pose,
            visible=visible)
        self.end_effector = rave_manipulator.GetEndEffector()

    @property
    def index(self):
        """Notably used to compute jacobians and hessians."""
        return self.end_effector.GetIndex()
