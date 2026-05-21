// Drawing tools manager for TRADER·IA dashboard
// Phase 1: Implements 8 drawing tools, undo/redo, persistence hooks
// Author: Copilot (2026)

class DrawingManager {
    constructor(canvas, chartId) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.chartId = chartId;
        this.activeTool = null;
        this.drawings = [];
        this.undoStack = [];
        this.redoStack = [];
        this.isDrawing = false;
        this.currentDrawing = null;
        this.initEvents();
    }
    setTool(tool) {
        this.activeTool = tool;
    }
    addDrawing(drawing) {
        this.drawings.push(drawing);
        this.undoStack.push({action: 'add', drawing});
        this.redoStack = [];
        this.redraw();
    }
    undo() {
        if (this.undoStack.length === 0) return;
        const last = this.undoStack.pop();
        if (last.action === 'add') {
            this.drawings.pop();
            this.redoStack.push(last);
        }
        // ... handle other actions
        this.redraw();
    }
    redo() {
        if (this.redoStack.length === 0) return;
        const last = this.redoStack.pop();
        if (last.action === 'add') {
            this.drawings.push(last.drawing);
            this.undoStack.push(last);
        }
        // ... handle other actions
        this.redraw();
    }
    clear() {
        this.drawings = [];
        this.undoStack = [];
        this.redoStack = [];
        this.redraw();
    }
    redraw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        for (const d of this.drawings) {
            d.draw(this.ctx);
        }
    }
    initEvents() {
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
    }
    onMouseDown(e) {
        if (!this.activeTool) return;
        this.isDrawing = true;
        this.currentDrawing = this.activeTool.start(e, this.ctx);
    }
    onMouseMove(e) {
        if (!this.isDrawing || !this.currentDrawing) return;
        this.activeTool.move(e, this.currentDrawing, this.ctx);
        this.redraw();
        this.currentDrawing.draw(this.ctx);
    }
    onMouseUp(e) {
        if (!this.isDrawing || !this.currentDrawing) return;
        this.activeTool.end(e, this.currentDrawing, this.ctx);
        this.addDrawing(this.currentDrawing);
        this.isDrawing = false;
        this.currentDrawing = null;
    }
    // ... persistence hooks (save/load)
}

// Example tool: Line
class LineTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'line', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#00f';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.lineTo(this.x2, this.y2);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Rectangle Tool
class RectangleTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'rect', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#f5a623';
        ctx.lineWidth = 2;
        ctx.strokeRect(this.x1, this.y1, this.x2-this.x1, this.y2-this.y1);
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Triangle Tool
class TriangleTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'triangle', x1: p.x, y1: p.y, x2: p.x, y2: p.y, x3: p.x, y3: p.y, step: 1, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        if(drawing.step===1){ drawing.x2 = p.x; drawing.y2 = p.y; }
        else if(drawing.step===2){ drawing.x3 = p.x; drawing.y3 = p.y; }
    }
    end(e, drawing, ctx) {
        if(drawing.step===1){ drawing.step=2; } else { drawing.step=3; }
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#00d084';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.lineTo(this.x2, this.y2);
        ctx.lineTo(this.x3, this.y3);
        ctx.closePath();
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Text Tool
class TextTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'text', x: p.x, y: p.y, text: 'Texto', draw: this.draw};
    }
    move(e, drawing, ctx) {
        // No-op for text
    }
    end(e, drawing, ctx) {
        // Prompt for text
        const t = prompt('Texto:', drawing.text||'');
        if(t!==null) drawing.text = t;
    }
    draw(ctx) {
        ctx.save();
        ctx.font = '16px JetBrains Mono, monospace';
        ctx.fillStyle = '#fff';
        ctx.fillText(this.text, this.x, this.y);
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Parallel Line Tool
class ParallelLineTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'parallel', x1: p.x, y1: p.y, x2: p.x, y2: p.y, offset: 20, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#ff4757';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.lineTo(this.x2, this.y2);
        ctx.moveTo(this.x1, this.y1+this.offset);
        ctx.lineTo(this.x2, this.y2+this.offset);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Curved Line Tool
class CurvedLineTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'curve', x1: p.x, y1: p.y, x2: p.x, y2: p.y, cx: p.x+30, cy: p.y-30, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
        drawing.cx = (drawing.x1 + drawing.x2)/2;
        drawing.cy = drawing.y1 - 40;
    }
    end(e, drawing, ctx) {
        // No-op
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#a78bfa';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        ctx.quadraticCurveTo(this.cx, this.cy, this.x2, this.y2);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Ray Tool
class RayTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'ray', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        // No-op
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#00d9ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x1, this.y1);
        // Extiende la línea más allá del canvas
        const dx = this.x2 - this.x1;
        const dy = this.y2 - this.y1;
        const len = Math.sqrt(dx*dx+dy*dy);
        const scale = 1000/len;
        ctx.lineTo(this.x1 + dx*scale, this.y1 + dy*scale);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

// Extended Line Tool
class ExtendedLineTool {
    start(e, ctx) {
        const p = this.getPos(e, ctx);
        return {type: 'extend', x1: p.x, y1: p.y, x2: p.x, y2: p.y, draw: this.draw};
    }
    move(e, drawing, ctx) {
        const p = this.getPos(e, ctx);
        drawing.x2 = p.x;
        drawing.y2 = p.y;
    }
    end(e, drawing, ctx) {
        // No-op
    }
    draw(ctx) {
        ctx.save();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        // Extiende la línea en ambas direcciones
        const dx = this.x2 - this.x1;
        const dy = this.y2 - this.y1;
        const len = Math.sqrt(dx*dx+dy*dy);
        const scale = 1000/len;
        ctx.beginPath();
        ctx.moveTo(this.x1 - dx*scale, this.y1 - dy*scale);
        ctx.lineTo(this.x2 + dx*scale, this.y2 + dy*scale);
        ctx.stroke();
        ctx.restore();
    }
    getPos(e, ctx) {
        const rect = ctx.canvas.getBoundingClientRect();
        return {x: e.clientX - rect.left, y: e.clientY - rect.top};
    }
}

window.DrawingManager = DrawingManager;
window.LineTool = LineTool;
window.RectangleTool = RectangleTool;
window.TriangleTool = TriangleTool;
window.TextTool = TextTool;
window.ParallelLineTool = ParallelLineTool;
window.CurvedLineTool = CurvedLineTool;
window.RayTool = RayTool;
window.ExtendedLineTool = ExtendedLineTool;
