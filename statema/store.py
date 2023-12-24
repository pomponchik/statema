import json
import inspect
from threading import Lock
from collections import UserDict
from typing import Hashable, Callable, Any, Dict

from statema import Point


class MapDict(UserDict):
    def __init__(self, another_dict: Dict[Hashable, Any], function: Callable[[Any], Any]):
        self.function = function
        super().__init__(another_dict)

    def __getitem__(self, key: Hashable):
        value = self.data.__getitem__(key)
        changed_value = self.function(value)
        return changed_value


class Store:
    def __init__(self, **kwargs):
        """
        Здесь происходит оповещение пунктов настроек об экземпляре класса настроек, а также о прочих важных аспектах, чтобы те могли обращаться друг к другу при необходимости.

        К примеру, некоторые пункты настроек нельзя изменять без проверки на то, был ли уже записан первый лог. В свою очередь, событие записи первого лога изменяет пункт настроек 'started' на значение True. Прочие пункты настроек могут обращаться к данному и поднимать исключение, если их нельзя изменять после записи первого лога.
        Т. к. это синглтон, операция оповещения проделывается ровно один раз - за это отвечает флаг self.points_are_informed.
        """
        mro_dicts = {}
        for Class in reversed(type(self).__mro__):
            mro_dicts.update({key: value for key, value in Class.__dict__.items() if isinstance(value, Point)})
        self.__points__ = mro_dicts
        #self.__points__ = MapDict(
        #    mro_dicts,
        #    lambda x: x.__get__(),
        #)

        for name, point in self.__points__.items():
            point.set_store_object(self)
            point.set_name(name)
        for name, point in self.__points__.items():
            point.share_lock_object()
        for name, point in self.__points__.items():
            if point.do_action_first_time:
                point.do_action(None, point.value)

#    def __getitem__(self, key):
#        """
#        Получение текущего значения пункта настроек по его названию.
#
#        Список допустимых названий пунктов настроек см. в SettingsStore.points.
#        В случае запроса по любому другому ключу - поднимется KeyError.
#        Считывание настроек является неблокирующей операцией (за исключением случаев, когда при инициализации пункта настроек был установлен режим read_lock == True).
#        """
#        point = self._get_point(key)
#        return point.__get__()

    def __setitem__(self, key, value):
        """
        Устанавливаем новое значение пункта настроек по его названию.

        По умолчанию у каждого пункта настроек есть дефолтное значение.
        Каждое новое значение проверяется на соответствие некоему формату. Скажем, если конкретный пункт предполагает число, а пользователь передает строку - будет поднято исключение с сообщением о неправильном формате. Также производится проверка на конфликты с другими полями настроек.
        Список допустимых названий пунктов настроек см. в SettingsStore.points. В случае использования любого другого ключа - поднимется KeyError.
        При установке нового значения пункта настроек, блокируется только данный пункт. Прочие пункты настроек в этот момент можно изменять из других потоков. Старая настройка доступна для считывания, пока устанавливается новое значение, то есть блокировка распространяется только на операции записи. Однако для отдельных пунктов настроек чтение может быть заблокировано на время, пока другой поток производит запись - см. пункты с аргументом read_lock == True.
        """
        point = self._get_point(key)
        point.__set__(value)

    def __contains__(self, key):
        """
        Проверка того, что переданное название пункта настроек существует.
        """
        return key in self.__points__

    def __str__(self):
        """
        Распечатываем текущее состояние настроек.
        """
        data = {key: self._force_get(key) for key in self.__points__}
        strings = {key: f'"{value}"' for key, value in data.items()}
        for key, value in strings.items():
            data[key] == strings[key]
        data = [f'{key} = {value}' for key, value in data.items()]
        data = ', '.join(data)
        return f'<SettingStore object with data: {data}>'

    def _force_get(self, key):
        """
        Получение текущего значения пункта настроек по его названию, с игнорированием возможного режима блокировки на чтение.
        Даже если на чтение стоит блокировка, значение будет считано в обход.

        Использовать данный метод следует с большой осторожностью. Основной ожидаемый кейс использования - когда функции внутри функции, обозначенной для пункта настроек как action, используется считывание значения данного пункта. При обычном способе получения значения, если там установлен режим защищенного чтения, возникнет взаимоблокировка (deadlock), а данный метод позволяет ее избежать.
        """
        point = self._get_point(key)
        return point.unlocked_get()

    def _get_point(self, key):
        """
        Получаем объект поля по его названию.

        Важно отличать объекты полей от их содержимого. Объект поля всегда относится к классу SettingPoint, а содержимое поле - те данные, которые помещены в объект и собственно используются в качестве текущего значения настройки.
        """
        if key not in self.__points__:
            raise KeyError(f'{key} - there is no settings point with this name.')
        return self.__points__[key]
