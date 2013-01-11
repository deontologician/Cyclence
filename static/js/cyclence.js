/*
Copyright 2013 Josh Kuhn

This file is part of Cyclence.

Cyclence is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option)
any later version.

Cyclence is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
more details.

You should have received a copy of the GNU Affero General Public License
along with Cyclence.  If not, see <http://www.gnu.org/licenses/>.
*/

Cycl = Cycl || {};

Cycl.today = function(){
    var d = new Date()
    return '' + d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
}
