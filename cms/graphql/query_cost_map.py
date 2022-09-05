"""Costs map used by query complexity validator.

It's three levels deep dict of dicts:

- Type
- Fields
- Complexity

To set complexity cost for querying a field "likes" on type "User":

{
    "User": {
        "likes": {"complexity": 2}
    }
}

Querying above field will not increase query complexity by 1.

If field's complexity should be multiplied by value of argument (or arguments),
you can specify names of those arguments in "multipliers" list:

{
    "Query": {
        "products": {"complexity": 1, "multipliers": ["first", "last"]}
    }
}

This will result in following queries having cost of 100:

{ products(first: 100) { edges: { id } } }

{ products(last: 100) { edges: { id } } }

{ products(first: 10, last: 10) { edges: { id } } }

Notice that complexity is in last case is multiplied by all arguments.

Complexity is also multiplied recursively:

{
    "Query": {
        "products": {"complexity": 1, "multipliers": ["first", "last"]}
    },
    "Product": {
        "shippings": {"complexity": 1},
    }
}

This query will have cost of 200 (100 x 2 for each product):

{ products(first: 100) { complexity } }
"""

COST_MAP = {
    "Query": {
        "address": {"complexity": 1},
        "addressValidationRules": {"complexity": 1},
        "app": {"complexity": 1},
        "appExtension": {"complexity": 1},
        "appExtensions": {"complexity": 1, "multipliers": ["first", "last"]},
        "apps": {"complexity": 1, "multipliers": ["first", "last"]},
        "appsInstallations": {"complexity": 1},        
        "channel": {"complexity": 1},
        "channels": {"complexity": 1},        
        "customers": {"complexity": 1, "multipliers": ["first", "last"]},
        "me": {"complexity": 1},
        "menu": {"complexity": 1},
        "menuItem": {"complexity": 1},
        "menuItems": {"complexity": 1, "multipliers": ["first", "last"]},
        "menus": {"complexity": 1, "multipliers": ["first", "last"]},        
        "page": {"complexity": 1},
        "pages": {"complexity": 1, "multipliers": ["first", "last"]},
        "pageType": {"complexity": 1},
        "pageTypes": {"complexity": 1, "multipliers": ["first", "last"]},        
        "post": {"complexity": 1},
        "posts": {"complexity": 1, "multipliers": ["first", "last"]},
        "postType": {"complexity": 1},
        "postTypes": {"complexity": 1, "multipliers": ["first", "last"]},
        "permissionGroup": {"complexity": 1},
        "permissionGroups": {"complexity": 1, "multipliers": ["first", "last"]},
        "plugin": {"complexity": 1},
        "plugins": {"complexity": 1, "multipliers": ["first", "last"]},
        "staffUsers": {"complexity": 1, "multipliers": ["first", "last"]},       
        "translation": {"complexity": 1},
        "translations": {"complexity": 1, "multipliers": ["first", "last"]},
        "user": {"complexity": 1},       
        "webhook": {"complexity": 1},
    },
    "App": {
        "extensions": {"complexity": 1},
        "tokens": {"complexity": 1},
        "webhooks": {"complexity": 1},
    },    
    "Group": {
        "permissions": {"complexity": 1},
        "users": {"complexity": 1},
    },
    "Menu": {
        "items": {"complexity": 1},
    },
    "MenuItem": {
        "children": {"complexity": 1},
        "menu": {"complexity": 1},
        "page": {"complexity": 1},
        "parent": {"complexity": 1},
    },    
    "Page": {
        "pageType": {"complexity": 1},
    },
    "PageType": {
    },
    "Post": {
        "postType": {"complexity": 1},
    },
    "PostType": {
    },
    "PostMedia": {
        "url": {"complexity": 1},
    },    
    "User": {
        "avatar": {"complexity": 1},       
        "editableGroups": {"complexity": 1},
        "events": {"complexity": 1},
        "permissionGroups": {"complexity": 1},
        "userPermissions": {"complexity": 1},
    },
}
