import random
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, CallbackContext
)

# Define conversation states
STATE_BOMB, STATE_CLIENT, STATE_SERVER, STATE_BET = range(4)

# --- Utility Functions ---

def generate_grid(grid_size: int, bombs_count: int, seed) -> list:
    random.seed(seed)
    safe_count = grid_size**2 - bombs_count
    grid = ['safe'] * safe_count + ['bomb'] * bombs_count
    random.shuffle(grid)
    return [grid[i:i + grid_size] for i in range(0, len(grid), grid_size)]

def guess_safe_spots(grid: list, bombs_count: int) -> list:
    SAFE_BLOCK_RANGES = {
        1: (7, 12),
        2: (6, 9),
        3: (5, 5),
        4: (3, 4),
        5: (2, 3),
        10: (2, 2),
        20: (1, 1)
    }
    if bombs_count in SAFE_BLOCK_RANGES:
        low, high = SAFE_BLOCK_RANGES[bombs_count]
    else:
        total_safe = 25 - bombs_count
        low = max(1, total_safe // 2)
        high = total_safe
    safe_spots_count = random.randint(low, high)
    
    safe_spots = []
    rows = len(grid)
    cols = len(grid[0])
    attempts = 0
    while len(safe_spots) < safe_spots_count and attempts < 100:
        row = random.randint(0, rows - 1)
        col = random.randint(0, cols - 1)
        if (row, col) == (0, 0):
            attempts += 1
            continue
        if grid[row][col] == 'safe' and (row, col) not in safe_spots:
            safe_spots.append((row, col))
        attempts += 1
    return safe_spots

def display_safe_spots(safe_spots: list) -> str:
    result = "🔹 Safe Spot Predictions:
"
    for spot in safe_spots:
        result += f"👉 Row {spot[0] + 1}, Column {spot[1] + 1}
"
    return result

def compute_combined_seed(client_seed: str, server_seed: str) -> str:
    return client_seed + server_seed

# --- Conversation Handler Functions ---

async def bet_command(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Please enter the number of bombs (1-24):")
    return STATE_BOMB

async def bomb_input(update: Update, context: CallbackContext) -> int:
    try:
        bombs_count = int(update.message.text)
        if bombs_count < 1 or bombs_count > 24:
            await update.message.reply_text("Invalid bomb count. Enter a number between 1 and 24:")
            return STATE_BOMB
        context.user_data['bombs_count'] = bombs_count
        await update.message.reply_text("Bomb count set.
Now, enter your Active Client Seed:")
        return STATE_CLIENT
    except ValueError:
        await update.message.reply_text("Please enter a valid number for bomb count:")
        return STATE_BOMB

async def client_seed_input(update: Update, context: CallbackContext) -> int:
    client_seed = update.message.text.strip()
    if not client_seed:
        await update.message.reply_text("Please enter a valid Active Client Seed:")
        return STATE_CLIENT
    context.user_data['client_seed'] = client_seed
    await update.message.reply_text("Active Client Seed set.
Now, enter your Active Server Seed:")
    return STATE_SERVER

async def server_seed_input(update: Update, context: CallbackContext) -> int:
    server_seed = update.message.text.strip()
    if not server_seed:
        await update.message.reply_text("Please enter a valid Active Server Seed:")
        return STATE_SERVER
    context.user_data['server_seed'] = server_seed
    combined_seed = compute_combined_seed(context.user_data['client_seed'], server_seed)
    context.user_data['combined_seed'] = combined_seed
    await update.message.reply_text("Active Server Seed set.
Now, enter your bet amount:")
    return STATE_BET

async def bet_input(update: Update, context: CallbackContext) -> int:
    try:
        bet_amount = float(update.message.text)
        if bet_amount <= 0:
            await update.message.reply_text("Bet amount must be a positive number. Please enter again:")
            return STATE_BET
        context.user_data['bet_amount'] = bet_amount
        
        grid_size = 5
        bombs_count = context.user_data['bombs_count']
        combined_seed = context.user_data['combined_seed']
        
        grid = generate_grid(grid_size, bombs_count, combined_seed)
        safe_spots = guess_safe_spots(grid, bombs_count)
        result = display_safe_spots(safe_spots)
        result += f"
💰 Bet Amount: ${bet_amount}"
        await update.message.reply_text(result)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number for bet amount:")
        return STATE_BET

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def start_command(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Welcome to the Minesweeper Bot! Type /bet to start the process.")
    return ConversationHandler.END

def main() -> None:
    from telegram.ext import ConversationHandler
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("bet", bet_command)],
        states={
            STATE_BOMB: [MessageHandler(filters.TEXT & ~filters.COMMAND, bomb_input)],
            STATE_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_seed_input)],
            STATE_SERVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, server_seed_input)],
            STATE_BET: [MessageHandler(filters.TEXT & ~filters.COMMAND, bet_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(conv_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()
