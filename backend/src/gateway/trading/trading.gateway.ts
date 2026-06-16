import { Logger } from '@nestjs/common';
import {
  OnGatewayConnection,
  OnGatewayInit,
  WebSocketGateway,
  WebSocketServer,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { RedisService } from '../../redis/redis.service';

const REDIS_CHANNELS = [
  'candles:*',
  'news:*',
  'calendar:*',
  'signal:*',
  'trade:*',
  'bot:state:*',
  'system:*',
];

@WebSocketGateway({
  cors: {
    origin: process.env.CORS_ORIGIN ?? 'http://localhost:5173',
  },
})
export class TradingGateway implements OnGatewayInit, OnGatewayConnection {
  private readonly logger = new Logger(TradingGateway.name);

  @WebSocketServer()
  server: Server;

  constructor(private readonly redisService: RedisService) {}

  afterInit(): void {
    void this.redisService.subscribe('*', (channel, message) => {
      const eventType = this.resolveEventType(channel);
      this.logger.debug(`Relay ${channel} -> ${eventType}`);
      this.server.emit(eventType, { channel, data: this.parseMessage(message) });
    });
    this.logger.log(
      `WebSocket gateway ready — relaying Redis channels: ${REDIS_CHANNELS.join(', ')}`,
    );
  }

  handleConnection(client: Socket): void {
    this.logger.log(`Client connected: ${client.id}`);
  }

  private resolveEventType(channel: string): string {
    if (channel.startsWith('bot:state:')) return 'bot:state';
    if (channel.startsWith('trade:opened:')) return 'trade:opened';
    if (channel.startsWith('trade:closed:')) return 'trade:closed';
    if (channel.startsWith('signal:')) return 'signal:generated';
    if (channel.startsWith('candles:')) return 'candle:close';
    if (channel === 'news:scored') return 'news:scored';
    if (channel === 'system:error') return 'system:error';
    return channel;
  }

  private parseMessage(message: string): unknown {
    try {
      return JSON.parse(message) as unknown;
    } catch {
      return message;
    }
  }
}
