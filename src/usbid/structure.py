"""
USB file system (From http://www.linux-usb.org/FAQ.html)
--------------------------------------------------------

# ls  /sys/bus/usb/devices/
1-0:1.0      1-1.3        1-1.3.1:1.0  1-1:1.0
1-1          1-1.3.1      1-1.3:1.0    usb1

The names that begin with "usb" refer to USB controllers. More accurately, they
refer to the "root hub" associated with each controller. The number is the USB
bus number. In the example there is only one controller, so its bus is number
1. Hence the name "usb1".

"1-0:1.0" is a special case. It refers to the root hub's interface. This acts
just like the interface in an actual hub an almost every respect; see below.

All the other entries refer to genuine USB devices and their interfaces.
The devices are named by a scheme like this:

    bus-port.port.port ...

In other words, the name starts with the bus number followed by a '-'. Then
comes the sequence of port numbers for each of the intermediate hubs along the
path to the device.

For example, "1-1" is a device plugged into bus 1, port 1. It happens to be a
hub, and "1-1.3" is the device plugged into port 3 of that hub. That device is
another hub, and "1-1.3.1" is the device plugged into its port 1.

The interfaces are indicated by suffixes having this form:

    :config.interface

That is, a ':' followed by the configuration number followed by '.' followed
by the interface number. In the above example, each of the devices is using
configuration 1 and this configuration has only a single interface, number 0.
So the interfaces show up as;

    1-1:1.0        1-1.3:1.0        1-1.3.1:1.0

A hub will never have more than a single interface; that's part of the USB
spec. But other devices can and do have multiple interfaces (and sometimes
multiple configurations). Each interface gets its own entry in sysfs and can
have its own driver.

Examples
--------

idProduct: 6010
idVendor: 0403
Product Name: FT2232C Dual USB-UART/FIFO IC
Vendor Name: Future Technology Devices International, Ltd

# ls  /sys/bus/usb/devices/
3-2       -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2
3-2:1.0   -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2:1.0
3-2:1.1   -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2:1.1

idProduct: 6001
idVendor: 0403
Product Name: FT232 USB-Serial (UART) IC
Vendor Name: Future Technology Devices International, Ltd

# ls  /sys/bus/usb/devices/
3-2       -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2
3-2.1     -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2.1
3-2:1.0   -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2:1.0
3-2.1:1.0 -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2.1/3-2.1:1.0
3-2.2     -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2.2
3-2.2:1.0 -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2.2/3-2.2:1.0
3-2.3     -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2.3
3-2.3:1.0 -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2.3/3-2.3:1.0
3-2.4     -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2.4
3-2.4:1.0 -> ../../../devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2.4/3-2.4:1.0
"""

import os
import re


USB_FS_ROOT = '/sys/bus/usb/devices'
IS_BUS = re.compile("^usb\d$")
IS_BUS_PORT = re.compile("^\d-\d$")
IS_SUB_PORT = re.compile("^\d-\d(\.\d)*$")
IS_INTERFACE = re.compile("^\d-\d(\.\d)*:\d.\d$")


class Container(object):
    """Mixin for container objects.
    """
    name = None
    parent = None

    def keys(self):
        return list(self.__iter__())

    def values(self):
        return [self[key] for key in self]

    def items(self):
        return [(key, self[key]) for key in self]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __iter__(self):
        raise NotImplementedError()

    def __getitem__(self, key):
        raise NotImplementedError()


class FSLocation(object):
    """Mixin for objects with a file system location.
    """
    fs_path = None

    @property
    def fs_name(self):
        if self.fs_path.find(os.path.sep) > -1:
            return self.fs_path[self.fs_path.rfind(os.path.sep) + 1:]

    @property
    def fs_parent(self):
        if self.fs_path.find(os.path.sep) > -1:
            return self.fs_path[:self.fs_path.rfind(os.path.sep)]


class FileAttributes(FSLocation):
    """Mixin for objects handling attributes stored in files. A single file
    represents a single attribute where the file name is the attribute name
    and the file content is the attribute value.
    """
    __file_attributes__ = []

    def __getattribute__(self, name):
        if name in object.__getattribute__(self, '__file_attributes__'):
            try:
                with open(os.path.join(self.fs_path, name), 'r') as file:
                    return file.read().strip('\n').strip()
            except IOError:
                return None
        return object.__getattribute__(self, name)


class ReprMixin(object):

    def __repr__(self):
        return '<{0}.{1} [{2}] at {3}>'.format(
            self.__module__,
            self.__class__.__name__,
            self.fs_name,
            id(self)
        )

    def printtree(self, indent=0):
        print '{0}{1}'.format(indent * ' ', repr(self))
        manufacturer = getattr(self, 'manufacturer', None)
        if manufacturer is not None:
            print '{0}- {1}'.format((indent + 4) * ' ', manufacturer)
        product = getattr(self, 'product', None)
        if product is not None:
            print '{0}- {1}'.format((indent + 4) * ' ', product)
        if isinstance(self, InterfaceProvider):
            for iface in sorted(self.interfaces, key=lambda x: x.fs_name):
                print '{0}{1}'.format((indent + 2) * ' ', repr(iface))
                tty = iface.tty
                if tty:
                    print '{0}- {1}'.format((indent + 4) * ' ', tty)
        for node in sorted(self.values(), key=lambda x: x.fs_name):
            node.printtree(indent + 2)


class AggregatedInterfaces(object):

    def aggregated_interfaces(self, tty=False):
        def aggregate(node, ifaces):
            for child in node.values():
                if isinstance(child, InterfaceProvider):
                    for iface in child.interfaces:
                        if tty and iface.tty is None:
                            continue
                        ifaces.append(iface)
                aggregate(child, ifaces)
        ifaces = []
        aggregate(self, ifaces)
        return ifaces


class USB(Container, FSLocation, AggregatedInterfaces, ReprMixin):
    """Object representing USB filsystem root.
    """

    def __init__(self, fs_path=USB_FS_ROOT):
        self.fs_path = fs_path

    def __iter__(self):
        for child in os.listdir(self.fs_path):
            if IS_BUS.match(child):
                yield child[3:]

    def __getitem__(self, key):
        bus_path = os.path.join(self.fs_path, 'usb{0}'.format(key))
        if not os.path.isdir(bus_path):
            raise KeyError(key)
        return Bus(name=key, parent=self, fs_path=bus_path)

    def __repr__(self):
        return '<{0}.{1} [{2}] at {3}>'.format(
            self.__module__,
            self.__class__.__name__,
            self.fs_path,
            id(self)
        )


class InterfaceProvider(Container, FSLocation):
    """Mixin for objects providing USB interfaces.
    """

    @property
    def interfaces(self):
        ifaces = []
        for child in os.listdir(self.fs_path):
            if IS_INTERFACE.match(child):
                iface_path = os.path.join(self.fs_path, child)
                ifaces.append(Interface(fs_path=iface_path))
        return ifaces


class Bus(FileAttributes, InterfaceProvider, ReprMixin):
    """Object representing a USB bus.
    """
    __file_attributes__ = [
        'authorized',
        'authorized_default',
        'avoid_reset_quirk',
        'bcdDevice',
        'bConfigurationValue',
        'bDeviceClass',
        'bDeviceProtocol',
        'bDeviceSubClass',
        'bmAttributes',
        'bMaxPacketSize0',
        'bMaxPower',
        'bNumConfigurations',
        'bNumInterfaces',
        'busnum',
        'dev',
        'devnum',
        'devpath',
        'idProduct',
        'idVendor',
        'ltm_capable',
        'manufacturer',
        'maxchild',
        'product',
        'quirks',
        'removable',
        'serial',
        'speed',
        'uevent',
        'urbnum',
        'version',
    ]

    def __init__(self, name, parent, fs_path):
        if not os.path.isdir(fs_path):
            raise ValueError('Invalid path given')
        self.name = name
        self.parent = parent
        self.fs_path = fs_path

    def __iter__(self):
        for child in os.listdir(self.fs_path):
            if IS_BUS_PORT.match(child):
                yield child[child.find('-') + 1:]

    def __getitem__(self, key):
        port_path = os.path.join(
            self.fs_path,
            '{0}-{1}'.format(self.name, key)
        )
        if not os.path.isdir(port_path):
            raise KeyError(key)
        return Port(name=key, parent=self, fs_path=port_path)


class Port(FileAttributes, InterfaceProvider, ReprMixin):
    """Object representing a USB port.
    """
    __file_attributes__ = [
        'authorized',
        'avoid_reset_quirk',
        'bcdDevice',
        'bConfigurationValue',
        'bDeviceClass',
        'bDeviceProtocol',
        'bDeviceSubClass',
        'bmAttributes',
        'bMaxPacketSize0',
        'bMaxPower',
        'bNumConfigurations',
        'bNumInterfaces',
        'busnum',
        'dev',
        'devnum',
        'devpath',
        'idProduct',
        'idVendor',
        'ltm_capable',
        'manufacturer',
        'maxchild',
        'product',
        'quirks',
        'removable',
        'serial',
        'speed',
        'uevent',
        'urbnum',
        'version',
    ]

    def __init__(self, name, parent, fs_path):
        if not os.path.isdir(fs_path):
            raise ValueError('Invalid path given')
        self.name = name
        self.parent = parent
        self.fs_path = fs_path

    def __iter__(self):
        for child in os.listdir(self.fs_path):
            if IS_SUB_PORT.match(child):
                yield child[child.rfind('.') + 1:]

    def __getitem__(self, key):
        port_path = os.path.join(
            self.fs_path,
            '{0}.{1}'.format(self.fs_name, key)
        )
        if not os.path.isdir(port_path):
            raise KeyError(key)
        return Port(name=key, parent=self, fs_path=port_path)


class Interface(FileAttributes, ReprMixin):
    """Object representing a USB interface.
    """
    __file_attributes__ = [
        'bAlternateSetting',
        'bInterfaceClass',
        'bInterfaceNumber',
        'bInterfaceProtocol',
        'bInterfaceSubClass',
        'bNumEndpoints',
        'interface',
        'modalias',
        'supports_autosuspend',
        'uevent',
    ]

    def __init__(self, fs_path):
        if not os.path.isdir(fs_path):
            raise ValueError('Invalid path given')
        self.fs_path = fs_path

    @property
    def tty(self):
        def match_tty(path):
            for child in os.listdir(path):
                if not child.startswith("tty"):
                    continue
                # final tty device
                if child != 'tty':
                    return child
                # search in tty sub directory
                return match_tty(os.path.join(path, child))
        return match_tty(self.fs_path)
