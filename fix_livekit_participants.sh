#!/bin/bash
# Quick fix for LiveKit Room participants issue
# Run this on the server to fix the AttributeError

echo "🔧 Fixing LiveKit Room participants issue..."

# Backup current file
cp cagent.py cagent.py.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"

# Fix 1: Change ctx.room.participants to ctx.room.num_participants in logging
sed -i 's/len(ctx\.room\.participants)/ctx.room.num_participants/g' cagent.py
echo "✅ Fixed participants logging"

# Fix 2: Update participant access method
sed -i 's/hasattr(ctx\.room, "participants") and ctx\.room\.participants:/getattr(ctx.room, "remote_participants", None) is not None:/g' cagent.py
sed -i 's/for p in ctx\.room\.participants\.values():/for p in getattr(ctx.room, "remote_participants", {}).values():/g' cagent.py
echo "✅ Fixed participant access"

# Check syntax
if python3 -m py_compile cagent.py; then
    echo "✅ Syntax check passed"
else
    echo "❌ Syntax error - restoring backup"
    cp cagent.py.backup.* cagent.py
    exit 1
fi

echo "🎉 Fix completed successfully!"
echo "📋 Next steps:"
echo "1. pm2 restart 5"
echo "2. pm2 log 5 --lines 50"
echo "3. Test with a call to verify fix"

# Show the changes made
echo ""
echo "📝 Changes made:"
echo "- Fixed Room.participants → Room.num_participants"
echo "- Fixed participant access to use remote_participants"
echo "- Created backup: cagent.py.backup.*"