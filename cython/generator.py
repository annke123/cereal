#!/usr/bin/env python3

import capnp
from cereal import car

pxd = """from libcpp cimport bool
from libc.stdint cimport *

cdef extern from "capnp_wrapper.h":
    cdef T ReaderFromBytes[T](char* dat, size_t sz)

"""

TYPE_LOOKUP = {
  'float32': 'float',
  'float64': 'double',
  'bool': 'bool',
  'int16': 'int16_t',
}

if __name__ == "__main__":
  # TODO: get capnp name from root schema
  tp = car.CarState
  capnp_name, class_name = tp.schema.node.displayName.split(':')
  capnp_name, _ = capnp_name.split('.')

  pxd += f"cdef extern from \"../gen/cpp/{capnp_name}.capnp.c++\":\n    pass\n\n"
  pxd += f"cdef extern from \"../gen/cpp/{capnp_name}.capnp.h\":\n"

  pyx = f"from {capnp_name} cimport ReaderFromBytes, {class_name}Reader\n\n"

  for node in car.schema.node.nestedNodes:
    tp = getattr(car, node.name)

    capnp_name, class_name = tp.schema.node.displayName.split(':')
    capnp_name, _ = capnp_name.split('.')

    pxd += f"    cdef cppclass {class_name}Reader \"cereal::{class_name}::Reader\":\n"

    pyx += f"from {capnp_name} cimport {class_name}Reader\n\n"
    pyx += f"cdef class {class_name}(object):\n"
    pyx += f"    cdef {class_name}Reader reader\n\n"
    pyx += f"    def __init__(self, s):\n"
    pyx += f"        self.reader = ReaderFromBytes[{class_name}Reader](s, len(s))\n\n"

    added_fields = False

    print(class_name)
    for field in tp.schema.fields_list:
      name = field.proto.name

      try:
        if len(field.schema.union_fields):
          continue  # TODO: handle unions

        # Normal struct
      except (capnp.lib.capnp.KjException, AttributeError):
        pass

      tp = field.proto.slot.type._which_str()
      print(tp, name)

      if tp in ['list', 'struct', 'enum', 'text']:
        continue

      name_cap = name[0].upper() + name[1:]

      tp = TYPE_LOOKUP[tp]
      pxd += 8 * " " + f"{tp} get{name_cap}()\n"
      pyx += 4 * " " + f"@property\n"
      pyx += 4 * " " + f"def {name}(self):\n"
      pyx += 8 * " " + f"return self.reader.get{name_cap}()\n\n"
      added_fields = True

    if not added_fields:
      pxd += 8 * " " + "pass\n\n"
    else:
      pxd += "\n"


  with open('car.pxd', 'w') as f:
    f.write(pxd)

  with open('car.pyx', 'w') as f:
    f.write(pyx)
