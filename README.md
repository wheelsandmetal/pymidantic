# PyMidantic

A module to allow migrating pydantic model dumps to different versions of
themselves. Allowing you to easily maintain older data output versions.

## Usage

You can use the `migrate` decorator to define a migration on a child of
`Migratable` between 2 versions. This defines an edge in a DAG where each node is
a different version of your class. To output a different version you can call
the `dump_verision` method on your class, and if a valid path exists from the
version of the instance to your requested version you'll get the output at that
version.

While it's possible to use the `migrate` decorator to define "upgrades" to your
data and then output at the latest as required, it's better used to support
older versions. Using it this way means the objects you're using in the code
will reflect the latest data, minimise the need pass additional_data (upgrades
tend not to remove data), and contain the version handling to the output part of
your code. In the example below we have a `Car` model to which we've recently
added the `engine_type` feature. For some reason some customers/clients aren't
ready to have this feature yet, and so we define a migration to allow outputing
a `Car` at verion `1.0.0` for them.

```python
class Car(Migratable):
    '''
    ChangeLog:
        - 2.0.0
            Add engine type
    '''

    _version: ClassVar[str] = "2.0.0"

    name: str
    engine_type: str


@migrate(Car, "2.0.0", "1.0.0")
def remove_engine_type(attrs: dict, addtional_data: dict) -> None:
    attrs.pop("engine_type", None)

car = Car(name="Model 3", engine_type="electric")

output = car.dump_version("1.0.0")
assert output == {"name": "Model 3"}
```

See test_migdantic.py for more examples

### Type hint `additional_data`

You can provide overloads to the `dump_version` method if you want to type hint
the additinal data that's passed in.

```python
class Car(Migratable):
    '''
    ChangeLog:
        - 3.0.0
            Remove engine type
        - 2.0.0
            Add engine type
    '''

    _version: ClassVar[str] = "3.0.0"

    name: str

    class CarEngineType(TypedDict):
        engine_type: int

    @overload
    def dump_version(
        self,
        version: Literal["2.0.0"],
        additional_data: CarEngineType,
        **kwargs,
    ) -> dict[str, Any]: ...

    @overload
    def dump_version(
        self,
        version: Literal["1.0.0"],
        additional_data: None = ...,
        **kwargs,
    ) -> dict[str, Any]: ...

    def dump_version(
        self,
        version: str,
        additional_data: Mapping[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        return super().dump_version(version, additional_data, **kwargs)

@migrate(Car, "3.0.0", "2.0.0")
def remove_engine_type(attrs: dict[str, Any], additional_data: dict[str, Any]) -> None:
    attrs["engine_type"] = additional_data["engine_type"]

@migrate(Car, "3.0.0", "1.0.0")
@migrate(Car, "2.0.0", "1.0.0")
def remove_engine_type(attrs: dict[str, Any], additional_data: dict[str, Any]) -> None:
    attrs.pop("engine_type", None)

Car(name="Ford F150").dump_version("2.0.0") # no matching overloads!
Car(name="Ford F150").dump_version("2.0.0", {"engne_type": "gas"}) # "engne_type" is an undefined item in type "CarEngineType"

# Note that we must provide the "shortcut" migration in order to skip over version "2.0.0"
assert {"name": "Ford F150"} == Car(name="Ford F150").dump_version("1.0.0") # No type errors!
```
