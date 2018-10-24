#External Imports
import libtcodpy as libtcod

#Project Imports
from entity import Entity, get_blocking_entities_at_location
from input_handlers import handle_keys
from map_objects.game_map import GameMap
from render_functions import clear_all, render_all, RenderOrder
from fov_functions import initializ_fov, recompute_fov
from game_states import GameStates
from components.fighter import Fighter
from death_functions import kill_monster, kill_player
from game_messages import Message, MessageLog
from components.inventory import Inventory

def main():
    #initilize main variables
    screen_width = 80
    screen_height = 50

    bar_width = 20
    panel_height = 7
    panel_y = screen_height - panel_height

    message_x = bar_width + 2
    message_width = screen_width - bar_width - 2
    message_height = panel_height - 1

    map_width = 80
    map_height = 43

    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    fov_algorithm = 0
    fov_light_walls = True
    fov_radius = 10

    max_monsters_per_room = 3
    max_items_per_room = 2

    #define color palette
    colors = {
        'dark_wall': libtcod.Color(55, 50, 45),
        'dark_ground': libtcod.Color(15, 15, 15),
        'light_wall': libtcod.Color(70, 55, 40),
        'light_ground': libtcod.Color(30, 20, 15)
    }

    #Create Player
    fighter_component = Fighter(hp=30, defense=2, power=5)
    inventory_component = Inventory(26)
    player = Entity(0, 0, '@', libtcod.white, 'Player', blocks=True, render_order=RenderOrder.ACTOR,
                    fighter=fighter_component, inventory=inventory_component)
    entities = [player]
    player_won = False

    #set up screen
    libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
    libtcod.console_init_root(screen_width, screen_height, 'SimpleRogue', False)
    con = libtcod.console_new(screen_width, screen_height)
    panel = libtcod.console_new(screen_width, panel_height)

    key = libtcod.Key()
    mouse = libtcod.Mouse()

    #Generate map with entities
    game_map = GameMap(map_width, map_height)
    game_map.make_map(max_rooms, room_min_size, room_max_size, map_width, map_height, player,
                     entities, max_monsters_per_room, max_items_per_room)

    fov_recompute = True
    fov_map = initializ_fov(game_map)
    game_state = GameStates.PLAYERS_TURN
    previous_game_state = game_state

    message_log = MessageLog(message_x, message_width, message_height)

    # main game loop
    while not libtcod.console_is_window_closed():
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        
        #Update Display
        if fov_recompute:
            recompute_fov(fov_map, player.x, player.y, fov_radius, fov_light_walls, fov_algorithm)

        render_all(con, panel, entities, player, game_map, fov_map, fov_recompute, message_log,
                   screen_width, screen_height, bar_width, panel_height, panel_y, mouse, colors,
                   game_state)
        fov_recompute = False
        libtcod.console_flush()
        clear_all(con, entities)

        #Define possible actions
        action = handle_keys(key, game_state)

        move = action.get('move')
        pickup = action.get('pickup')
        show_inventory = action.get('show_inventory')
        inventory_index = action.get('inventory_index')
        exit = action.get('exit')
        fullscreen = action.get('fullscreen')

        #Clear the last set of results from actions
        player_turn_results = []

        #Handle actions

        #move the player
        if move and game_state == GameStates.PLAYERS_TURN:
            dx, dy = move
            destination_x = player.x + dx
            destination_y = player.y + dy

            if not game_map.is_blocked(destination_x, destination_y):
                target = get_blocking_entities_at_location(entities, destination_x, destination_y)

                if target:
                    player.fighter.attack(target)
                    attack_results = player.fighter.attack(target)
                    player_turn_results.extend(attack_results)
                else:
                    player.move(dx, dy)
                    fov_recompute = True
                
            game_state = GameStates.ENEMY_TURN
        
        #try to pick up something
        elif pickup and game_state == GameStates.PLAYERS_TURN:
            for entity in entities:
                if entity.item and entity.x == player.x and entity.y == player.y:
                    pickup_results = player.inventory.add_item(entity)
                    player_turn_results.extend(pickup_results)

                    break
            else:
                message_log.add_message(Message('There is nothing here to pick up.', libtcod.yellow))

        #display the inventory screen
        if show_inventory:
            if game_state != GameStates.SHOW_INVENTORY:
                previous_game_state = game_state
            game_state = GameStates.SHOW_INVENTORY

        #use an item in the inventory
        if inventory_index is not None and previous_game_state != GameStates.PLAYER_DEAD and inventory_index < len(
            player.inventory.items):
            item = player.inventory.items[inventory_index]
            player_turn_results.extend(player.inventory.use(item))

        #exit screen or close game
        if exit:
            if game_state == GameStates.SHOW_INVENTORY:
                game_state = previous_game_state
            else:
                return True

        #toggle full screen view
        if fullscreen:
            libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

        #Display results of player actions
        for player_turn_result in player_turn_results:
            message = player_turn_result.get('message')
            dead_entity = player_turn_result.get('dead')
            item_added = player_turn_result.get('item_added')
            item_consumed = player_turn_result.get('consumed')

            if message:
                message_log.add_message(message)

            if dead_entity:
                if dead_entity == player:
                    message, game_states = kill_player(dead_entity)
                else:
                    message = kill_monster(dead_entity)

                message_log.add_message(message)

            if item_added:
                entities.remove(item_added)
                game_state = GameStates.ENEMY_TURN

            if item_consumed:
                game_state = GameStates.ENEMY_TURN

        #check for win (player killed everything)
        fighter_count = 0
        for entity in entities:
            if entity.fighter is not None and entity.name != 'Player':
                fighter_count += 1
        if fighter_count == 0 and player_won != True:
            player_won = True
            message_log.add_message(Message("I hope you're proud of yourself...", libtcod.yellow))
            message_log.add_message(Message("You monster!", libtcod.red))


        #Handle enemy actions and display results
        if game_state == GameStates.ENEMY_TURN:
            for entity in entities:
                if entity.ai:
                    enemy_turn_results = entity.ai.take_turn(player, fov_map, game_map, entities)

                    for enemy_turn_result in enemy_turn_results:
                        message = enemy_turn_result.get('message')
                        dead_entity = enemy_turn_result.get('dead')

                        if message:
                            message_log.add_message(message)

                        if dead_entity:
                            if dead_entity == player:
                                message, game_state = kill_player(dead_entity)
                            else:
                                message = kill_monster(dead_entity)

                            message_log.add_message(message)

                            if game_state == GameStates.PLAYER_DEAD:
                                break
            else:
                game_state = GameStates.PLAYERS_TURN


if __name__ == '__main__':
    main()